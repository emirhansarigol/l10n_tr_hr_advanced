from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.fields import Date
import logging
import base64

# Zeep kütüphanesi SOAP servisleri için import ediliyor
try:
    from zeep import Client
    from zeep.helpers import serialize_object
    from zeep.exceptions import Fault
except ImportError:
    raise UserError(_("Lütfen sunucuya 'zeep' kütüphanesini kurun. (Komut: pip install zeep)"))

_logger = logging.getLogger(__name__)


class HrEmployeeSgkApi(models.Model):
    """ Personel Modelinin SGK Web Servis (API) Motorları (Zeep Altyapısı) """
    _inherit = 'hr.employee'

    def action_generate_sgk_entry(self):
        for emp in self:
            company = self.env.company
            if not company.sgk_kullanici_adi or not company.sgk_isyeri_kodu:
                raise UserError(_("Lütfen önce Şirket Ayarlarından SGK API şifrelerini tanımlayın!"))

            if not emp.identification_id:
                raise UserError(_("Personelin T.C. Kimlik Numarası (Kimlik No) alanı boş olamaz!"))

            wsdl_url = "https://sgkt.sgk.gov.tr/WS_SgkTescil4a/WS_SgkIseGirisService?wsdl"

            try:
                client = Client(wsdl_url)
            except Exception as e:
                raise UserError(_("SGK WSDL servisine bağlanılamadı! Detay: %s") % str(e))

            name_parts = emp.name.split() if emp.name else [' ', ' ']
            ad = " ".join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]
            soyad = name_parts[-1] if len(name_parts) > 1 else ' '

            giris_tarihi = emp.contract_date_start.strftime(
                '%d.%m.%Y') if emp.contract_date_start else Date.today().strftime('%d.%m.%Y')

            kullanici_bilgileri = {
                'kullaniciAdi': company.sgk_kullanici_adi,
                'isyeriKodu': company.sgk_isyeri_kodu,
                'sistemSifre': company.sgk_sistem_sifre,
                'isyeriSifre': company.sgk_isyeri_sifre,
                'isyeriSicil': company.sgk_isyeri_sicil
            }

            sigortali_listesi = {
                'tckimlikNo': int(emp.identification_id),
                'ad': ad,
                'soyad': soyad,
                'giristarihi': giris_tarihi,
                'sigortaliTuru': int(emp.sgk_sigorta_turu_id.code) if emp.sgk_sigorta_turu_id else 1,
                'gorevkodu': emp.sgk_gorev_kodu_id.code if emp.sgk_gorev_kodu_id else '',
                'meslekkodu': emp.sgk_meslek_kodu_id.code if emp.sgk_meslek_kodu_id else '',
                'csgbiskolu': emp.csgb_iskolu_id.code if emp.csgb_iskolu_id else '20',
                'eskihukumlu': 'E' if emp.sgk_eski_hukumlu else 'H',
                'ozurlu': 'E' if emp.sgk_engelli else 'H',
                'ogrenimkodu': emp.sgk_ogrenim_kodu or '',
                'mezuniyetbolumu': emp.sgk_mezuniyet_bolumu or '',
                'mezuniyetyili': int(emp.sgk_mezuniyet_yili) if emp.sgk_mezuniyet_yili else 0,
                'kismiSureliCalisiyormu': 'E' if emp.sgk_kismi_sureli else 'H',
                'kismiSureliCalismaGunSayisi': int(emp.sgk_kismi_sureli_gun) if emp.sgk_kismi_sureli_gun else 0
            }

            parametre = {
                'kullaniciBilgileri': kullanici_bilgileri,
                'sigortaliIseGirisListesi': sigortali_listesi,
                'ayniIsverenFarkliIsyeriNakil': 'E' if emp.sgk_nakil_gelis else 'H'
            }

            if emp.sgk_nakil_gelis and emp.sgk_nakil_geldigi_sicil:
                parametre['nakilGeldigiIsyeriSicil'] = emp.sgk_nakil_geldigi_sicil

            try:
                response = client.service.iseGirisKaydet(sgk4aIseGirisParametre=parametre)
                resp_dict = serialize_object(response)
            except Fault as fault:
                raise UserError(_("SGK SOAP Hatası: %s") % fault.message)
            except Exception as e:
                raise UserError(_("Beklenmeyen bir API hatası oluştu: %s") % str(e))

            # ================= YANIT KONTROLÜ (İŞE GİRİŞ) =================
            if resp_dict and isinstance(resp_dict, dict):
                hata_kodu = str(resp_dict.get('hataKodu', ''))
                hata_aciklamasi = resp_dict.get('hataAciklamasi', '')

                if hata_kodu not in ['0', '']:
                    raise UserError(_("SGK Sistem Hatası!\n\nKod: %s\nAçıklama: %s") % (hata_kodu, hata_aciklamasi))

                sonuc_verisi = resp_dict.get('sigortaliIseGirisSonuc')

                if isinstance(sonuc_verisi, dict):
                    islem_detayi = sonuc_verisi
                elif isinstance(sonuc_verisi, list) and len(sonuc_verisi) > 0:
                    islem_detayi = sonuc_verisi[0]
                else:
                    raise UserError(_("SGK ana paketi onayladı ancak detay okunamadı!\nYanıt: %s") % str(resp_dict))

                islem_sonucu = str(islem_detayi.get('islemSonucu', ''))
                islem_aciklamasi = islem_detayi.get('islemAciklamasi', '')
                referans = islem_detayi.get('referansKodu', '')

                if islem_sonucu == '-1' or referans in ['-1', -1, 0, '0', None, '']:
                    emp.message_post(body=f"❌ <b>SGK İşe Giriş Reddedildi!</b><br/>Detay: {islem_aciklamasi}")
                    raise UserError(_("SGK İşlem Reddedildi!\n\nDetay: %s") % islem_aciklamasi)

                emp.sgk_giris_referans = str(referans)
                emp.is_sgk_entry_generated = True

                emp.message_post(body=f"✅ <b>SGK İşe Giriş Başarılı!</b><br/>Referans Kodu: {referans}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('SGK İşlemi Başarılı'),
                        'message': _('İşe giriş işlemi başarıyla yapıldı. Referans: %s') % referans,
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }
            else:
                raise UserError(_("SGK'dan anlamsız bir yanıt döndü: %s") % str(resp_dict))

    def action_generate_sgk_exit(self):
        for emp in self:
            company = self.env.company
            if not company.sgk_kullanici_adi or not company.sgk_isyeri_kodu:
                raise UserError(_("Lütfen önce Şirket Ayarlarından SGK API şifrelerini tanımlayın!"))
            if not emp.identification_id:
                raise UserError(_("Personelin T.C. Kimlik Numarası (Kimlik No) alanı boş olamaz!"))
            if not emp.departure_date or not emp.iskur_reason_id:
                raise UserError(
                    _("Çıkış bildirgesi gönderebilmek için personelin 'Çıkış Tarihi' ve 'Çıkış Nedeni' dolu olmalıdır!"))

            wsdl_url = "https://sgkt.sgk.gov.tr/WS_SgkTescil4a/WS_SgkIstenCikisService?wsdl"

            try:
                client = Client(wsdl_url)
            except Exception as e:
                raise UserError(_("SGK WSDL servisine bağlanılamadı! Detay: %s") % str(e))

            cikis_tarihi = emp.departure_date.strftime('%d.%m.%Y')
            name_parts = emp.name.split() if emp.name else [' ', ' ']
            ad = " ".join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]
            soyad = name_parts[-1] if len(name_parts) > 1 else ' '

            kullanici_bilgileri = {
                'kullaniciAdi': company.sgk_kullanici_adi,
                'isyeriKodu': company.sgk_isyeri_kodu,
                'sistemSifre': company.sgk_sistem_sifre,
                'isyeriSifre': company.sgk_isyeri_sifre,
                'isyeriSicil': company.sgk_isyeri_sicil
            }

            bulundugumuz_donem = {
                'belgeturu': int(emp.sgk_belge_turu_id.code) if emp.sgk_belge_turu_id else 1,
                'hakedilenucret': float(emp.sgk_hakedilen_ucret or 0.0),
                'primikramiye': float(emp.sgk_prim_ikramiye or 0.0),
                'eksikgunsayisi': int(emp.sgk_eksik_gun_sayisi or 0),
                'eksikgunnedeni': int(emp.sgk_eksik_gun_nedeni_id.code) if emp.sgk_eksik_gun_nedeni_id else 0
            }

            onceki_donem_dict = {
                'belgeturu': int(emp.sgk_onceki_belge_turu_id.code) if emp.sgk_onceki_belge_turu_id else 1,
                'hakedilenucret': float(emp.sgk_onceki_hakedilen_ucret or 0.0),
                'primikramiye': float(emp.sgk_onceki_prim_ikramiye or 0.0),
                'eksikgunsayisi': int(emp.sgk_onceki_eksik_gun_sayisi or 0),
                'eksikgunnedeni': int(
                    emp.sgk_onceki_eksik_gun_nedeni_id.code) if emp.sgk_onceki_eksik_gun_nedeni_id else 0
            }

            sigortali_cikis_listesi = {
                'tckimlikNo': int(emp.identification_id),
                'ad': ad,
                'soyad': soyad,
                'istenCikisTarihi': cikis_tarihi,
                'istenCikisNedeni': str(emp.iskur_reason_id.code),
                'meslekkodu': emp.sgk_meslek_kodu_id.code if emp.sgk_meslek_kodu_id else '',
                'csgbiskolu': emp.csgb_iskolu_id.code if emp.csgb_iskolu_id else '20',
                'bulundugumuzDonem': bulundugumuz_donem,
                'oncekiDonem': onceki_donem_dict
            }

            parametre = {
                'kullaniciBilgileri': kullanici_bilgileri,
                'sigortaliIstenCikisListesi': sigortali_cikis_listesi
            }

            if emp.iskur_reason_id and emp.iskur_reason_id.code == '16':
                if not emp.sgk_nakil_gidis_sicil:
                    raise UserError(
                        _("İşten çıkış nedeni '16-Nakil' seçildiği için 'Nakil Gideceği İşyeri Sicil' alanını doldurmak zorundasınız!"))
                parametre['nakilGidecegiIsyeriSicil'] = emp.sgk_nakil_gidis_sicil

            try:
                response = client.service.istenCikisKaydet(sgk4aIstenCikisParametre=parametre)
                resp_dict = serialize_object(response)
            except Fault as fault:
                raise UserError(_("SGK SOAP Hatası: %s") % fault.message)
            except Exception as e:
                raise UserError(_("API Bağlantı Hatası: %s") % str(e))

            # ================= YANIT KONTROLÜ (İŞTEN ÇIKIŞ) =================
            if resp_dict and isinstance(resp_dict, dict):
                hata_kodu = str(resp_dict.get('hataKodu', ''))
                hata_aciklamasi = resp_dict.get('hataAciklamasi', '')

                if hata_kodu not in ['0', '']:
                    raise UserError(_("SGK Sistem Hatası!\n\nKod: %s\nAçıklama: %s") % (hata_kodu, hata_aciklamasi))

                sonuc_verisi = resp_dict.get('sigortaliIstenCikisSonuc')

                if isinstance(sonuc_verisi, dict):
                    islem_detayi = sonuc_verisi
                elif isinstance(sonuc_verisi, list) and len(sonuc_verisi) > 0:
                    islem_detayi = sonuc_verisi[0]
                else:
                    raise UserError(_("SGK ana paketi onayladı ancak detay okunamadı!\nYanıt: %s") % str(resp_dict))

                islem_sonucu = str(islem_detayi.get('islemSonucu', ''))
                islem_aciklamasi = islem_detayi.get('islemAciklamasi', '')
                referans = islem_detayi.get('referansKodu', '')

                if islem_sonucu == '-1' or referans in ['-1', -1, 0, '0', None, '']:
                    emp.message_post(body=f"❌ <b>SGK İşten Çıkış Reddedildi!</b><br/>Detay: {islem_aciklamasi}")
                    raise UserError(_("SGK İşlem Reddedildi!\n\nDetay: %s") % islem_aciklamasi)

                emp.sgk_cikis_referans = str(referans)
                emp.is_sgk_exit_generated = True

                emp.message_post(body=f"✅ <b>SGK İşten Çıkış Başarılı!</b><br/>Referans Kodu: {referans}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('SGK İşlemi Başarılı'),
                        'message': _('İşten çıkış başarıyla iletildi. Referans: %s') % referans,
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }
            else:
                raise UserError(_("SGK'dan anlamsız bir yanıt döndü: %s") % str(resp_dict))

    def action_download_sgk_entry_pdf(self):
        for emp in self:
            if not emp.sgk_giris_referans:
                raise UserError(_("SGK İşe Giriş Referans Kodu bulunamadı!"))

            company = self.env.company
            wsdl_url = "https://sgkt.sgk.gov.tr/WS_SgkTescil4a/WS_SgkIseGirisService?wsdl"

            try:
                client = Client(wsdl_url)
            except Exception as e:
                raise UserError(_("SGK WSDL servisine bağlanılamadı! Detay: %s") % str(e))

            kullanici_bilgileri = {
                'kullaniciAdi': company.sgk_kullanici_adi,
                'isyeriKodu': company.sgk_isyeri_kodu,
                'sistemSifre': company.sgk_sistem_sifre,
                'isyeriSifre': company.sgk_isyeri_sifre,
                'isyeriSicil': company.sgk_isyeri_sicil
            }

            try:
                response = client.service.iseGirisPdfDokum(kullanici=kullanici_bilgileri,
                                                           referansKodu=int(emp.sgk_giris_referans))
                resp_dict = serialize_object(response)
            except Fault as fault:
                raise UserError(_("SGK SOAP Hatası: %s") % fault.message)
            except Exception as e:
                raise UserError(_("API Hatası: %s") % str(e))

            pdf_b64 = resp_dict.get('pdfByteArray') if isinstance(resp_dict, dict) else None

            if pdf_b64:
                emp.doc_sgk_entry = base64.b64encode(pdf_b64)
                emp.doc_sgk_entry_fname = f"SGK_IseGiris_{emp.identification_id}.pdf"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('PDF İndirme Başarılı'),
                        'message': _('İşe giriş bildirgesi başarıyla Odoo evraklarına eklendi!'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }
            else:
                raise UserError(_("SGK belgeyi gönderdi ancak PDF verisi okunamadı. Yanıt: %s") % str(resp_dict))

    def action_download_sgk_exit_pdf(self):
        for emp in self:
            if not emp.sgk_cikis_referans:
                raise UserError(_("SGK İşten Çıkış Referans Kodu bulunamadı!"))

            company = self.env.company
            wsdl_url = "https://sgkt.sgk.gov.tr/WS_SgkTescil4a/WS_SgkIstenCikisService?wsdl"

            try:
                client = Client(wsdl_url)
            except Exception as e:
                raise UserError(_("SGK WSDL servisine bağlanılamadı! Detay: %s") % str(e))

            kullanici_bilgileri = {
                'kullaniciAdi': company.sgk_kullanici_adi,
                'isyeriKodu': company.sgk_isyeri_kodu,
                'sistemSifre': company.sgk_sistem_sifre,
                'isyeriSifre': company.sgk_isyeri_sifre,
                'isyeriSicil': company.sgk_isyeri_sicil
            }

            try:
                response = client.service.istenCikisPdfDokum(kullanici=kullanici_bilgileri,
                                                             referansKodu=int(emp.sgk_cikis_referans))
                resp_dict = serialize_object(response)
            except Fault as fault:
                raise UserError(_("SGK SOAP Hatası: %s") % fault.message)
            except Exception as e:
                raise UserError(_("API Hatası: %s") % str(e))

            pdf_b64 = resp_dict.get('pdfByteArray') if isinstance(resp_dict, dict) else None

            if pdf_b64:
                emp.doc_sgk_exit = base64.b64encode(pdf_b64)
                emp.doc_sgk_exit_fname = f"SGK_IstenCikis_{emp.identification_id}.pdf"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('PDF İndirme Başarılı'),
                        'message': _('İşten çıkış bildirgesi başarıyla Odoo evraklarına eklendi!'),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                    }
                }
            else:
                raise UserError(_("SGK belgeyi gönderdi ancak PDF verisi okunamadı. Yanıt: %s") % str(resp_dict))