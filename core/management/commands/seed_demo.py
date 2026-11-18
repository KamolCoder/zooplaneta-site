"""Fill an empty site with demo content in RU / UZ / EN so it can be reviewed.

    python manage.py seed_demo           # only on an empty site
    python manage.py seed_demo --reset   # delete all pages first (!)

Everything here is placeholder text: replace addresses, phones, promos and
vacancies with real ones in the CMS. Promos, news and vacancies are created in
RU and UZ only — the English version is for foreign partners.
"""
import datetime as dt
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from wagtail.models import Locale, Page, Site

from pages.models import (CareersPage, ContactPage, HomePage, NewsIndexPage, NewsPage, PartnersPage,
                          PromoIndexPage, PromoPage, StandardPage, VacancyPage)
from stores.models import StoreIndexPage, StorePage

L = ("ru", "uz", "en")


def rt(*paragraphs: str) -> str:
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


DISTRICTS = {
    "chilanzar": ("Чиланзар", "Chilonzor", "Chilanzar"),
    "yunusabad": ("Юнусабад", "Yunusobod", "Yunusabad"),
    "mirabad": ("Мирабад", "Mirobod", "Mirabad"),
    "mirzo": ("Мирзо-Улугбек", "Mirzo Ulugʻbek", "Mirzo Ulugbek"),
    "sergeli": ("Сергели", "Sergeli", "Sergeli"),
    "yakkasaray": ("Яккасарай", "Yakkasaroy", "Yakkasaray"),
    "shaykh": ("Шайхантахур", "Shayxontohur", "Shaykhantakhur"),
    "almazar": ("Алмазар", "Olmazor", "Almazar"),
    "uchtepa": ("Учтепа", "Uchtepa", "Uchtepa"),
    "yashnabad": ("Яшнабад", "Yashnobod", "Yashnabad"),
    "bektemir": ("Бектемир", "Bektemir", "Bektemir"),
    "yangihayot": ("Янгихаёт", "Yangihayot", "Yangihayot"),
}

# (name ru/uz/en, district, lat, lng, metro ru/uz/en or None, 24h)
STORES = [
    (("Чиланзар, 1-й квартал", "Chilonzor, 1-kvartal", "Chilanzar, block 1"), "chilanzar", 41.2856, 69.2045, ("Чиланзар", "Chilonzor", "Chilanzar"), False),
    (("Чиланзар, 9-й квартал", "Chilonzor, 9-kvartal", "Chilanzar, block 9"), "chilanzar", 41.2750, 69.1928, ("Новза", "Novza", "Novza"), False),
    (("Чиланзар, 19-й квартал", "Chilonzor, 19-kvartal", "Chilanzar, block 19"), "chilanzar", 41.2668, 69.1760, ("Олмазор", "Olmazor", "Olmazor"), False),
    (("Юнусабад, 4-й квартал", "Yunusobod, 4-kvartal", "Yunusabad, block 4"), "yunusabad", 41.3605, 69.2860, ("Юнусабад", "Yunusobod", "Yunusabad"), True),
    (("Юнусабад, 11-й квартал", "Yunusobod, 11-kvartal", "Yunusabad, block 11"), "yunusabad", 41.3700, 69.2950, ("Шахристан", "Shahriston", "Shakhriston"), False),
    (("Юнусабад, 19-й квартал", "Yunusobod, 19-kvartal", "Yunusabad, block 19"), "yunusabad", 41.3780, 69.3110, None, False),
    (("Мирабад", "Mirobod", "Mirabad"), "mirabad", 41.2990, 69.2810, ("Ойбек", "Oybek", "Oybek"), False),
    (("Госпитальный рынок", "Gospitalniy bozori", "Gospitalny market"), "mirabad", 41.2920, 69.2690, None, False),
    (("Мирзо-Улугбек, Буюк Ипак Йули", "Mirzo Ulugʻbek, Buyuk Ipak Yoʻli", "Mirzo Ulugbek, Buyuk Ipak Yuli"), "mirzo", 41.3260, 69.3330, ("Буюк Ипак Йули", "Buyuk Ipak Yoʻli", "Buyuk Ipak Yuli"), False),
    (("Мирзо-Улугбек, Карасу", "Mirzo Ulugʻbek, Qorasuv", "Mirzo Ulugbek, Karasu"), "mirzo", 41.3390, 69.3560, None, False),
    (("ТТЗ", "TTZ", "TTZ"), "mirzo", 41.3530, 69.3430, None, False),
    (("Сергели, 4-й квартал", "Sergeli, 4-kvartal", "Sergeli, block 4"), "sergeli", 41.2240, 69.2190, ("Сергели", "Sergeli", "Sergeli"), False),
    (("Сергели, 7-й квартал", "Sergeli, 7-kvartal", "Sergeli, block 7"), "sergeli", 41.2160, 69.2310, None, False),
    (("Яккасарай, Шота Руставели", "Yakkasaroy, Shota Rustaveli", "Yakkasaray, Shota Rustaveli"), "yakkasaray", 41.2880, 69.2510, ("Ойбек", "Oybek", "Oybek"), False),
    (("Кадышева", "Kadisheva", "Kadysheva"), "yakkasaray", 41.2760, 69.2560, None, False),
    (("Шайхантахур, Чорсу", "Shayxontohur, Chorsu", "Shaykhantakhur, Chorsu"), "shaykh", 41.3265, 69.2370, ("Чорсу", "Chorsu", "Chorsu"), False),
    (("Ц-5", "S-5", "C-5"), "shaykh", 41.3200, 69.2600, ("Алишер Навои", "Alisher Navoiy", "Alisher Navoi"), False),
    (("Алмазар, Беруни", "Olmazor, Beruniy", "Almazar, Beruni"), "almazar", 41.3450, 69.2050, ("Беруни", "Beruniy", "Beruni"), False),
    (("Каракамыш", "Qoraqamish", "Karakamysh"), "almazar", 41.3560, 69.1850, None, False),
    (("Учтепа, Фархадский рынок", "Uchtepa, Farhod bozori", "Uchtepa, Farkhad market"), "uchtepa", 41.2950, 69.1750, None, False),
    (("Яшнабад, Авиасозлар", "Yashnobod, Aviasozlar", "Yashnabad, Aviasozlar"), "yashnabad", 41.2980, 69.3350, ("Авиасозлар", "Aviasozlar", "Aviasozlar"), False),
    (("Бектемир", "Bektemir", "Bektemir"), "bektemir", 41.2300, 69.3350, None, False),
    (("Янгихаёт", "Yangihayot", "Yangihayot"), "yangihayot", 41.1950, 69.2050, None, False),
]

FEATURES = ("Ветаптека, Аквариумы, Оплата картой", "Veterinariya dorixonasi, Akvariumlar, Karta orqali toʻlov",
            "Vet pharmacy, Aquariums, Card payment")

BRANDS = ["Royal Canin", "Purina Pro Plan", "Hill's", "Brit", "Acana", "Monge", "Josera", "Whiskas",
          "Pedigree", "Tetra", "Vitakraft", "Trixie"]


class Command(BaseCommand):
    help = "Fill the site with demo content in RU / UZ / EN"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all existing pages first")

    @transaction.atomic
    def handle(self, *args, reset=False, **opts):
        if HomePage.objects.exists():
            if not reset:
                raise CommandError("The site already has content. Use --reset to wipe it (all pages are deleted).")
            for home in HomePage.objects.all():
                home.delete()

        self.loc = {code: Locale.objects.get_or_create(language_code=code)[0] for code in L}
        root = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        hostname, port = (site.hostname, site.port) if site else ("localhost", 80)
        # drop Wagtail's "Welcome" placeholder (and its Site row — recreated below)
        for old in root.get_children():
            old.delete()

        home = self.build_home(root)
        Site.objects.update_or_create(is_default_site=True, defaults={
            "hostname": hostname, "port": port, "root_page": home, "site_name": "Zoo Planeta"})

        about = self.build_about(home)
        stores = self.build_stores(home)
        promos = self.build_promos(home)
        careers = self.build_careers(home)
        partners = self.build_partners(home)
        self.build_contacts(home)
        self.build_news(home)
        self.build_privacy(home)
        self.fill_home(home, about, stores, promos, careers, partners)
        self.stdout.write(self.style.SUCCESS("Demo content created. Open /ru/ — and /cms/ to edit it."))

    # ── helpers ──────────────────────────────────────────────────────────────
    def publish(self, page):
        page.save_revision().publish()
        return page

    def add(self, parent, page):
        parent.add_child(instance=page)
        return self.publish(page)

    def translate(self, page, code, **fields):
        """Copy a RU page into another locale, set the translated fields and publish."""
        tr = page.copy_for_translation(self.loc[code], copy_parents=False).specific
        for key, value in fields.items():
            setattr(tr, key, value)
        tr.save()
        return self.publish(tr)

    def tri(self, parent, cls, langs=L, slug=None, **per_lang):
        """Create a page in RU (+ translations). per_lang: field=(ru, uz, en)."""
        ru_fields = {k: v[0] for k, v in per_lang.items()}
        page = self.add(parent, cls(slug=slug, locale=self.loc["ru"], **ru_fields))
        for i, code in enumerate(L):
            if code == "ru" or code not in langs:
                continue
            self.translate(page, code, **{k: v[i] for k, v in per_lang.items()})
        return page

    # ── pages ────────────────────────────────────────────────────────────────
    def build_home(self, root):
        home = HomePage(title="Zoo Planeta", slug="home", locale=self.loc["ru"],
                        seo_title="Zoo Planeta — сеть зоомагазинов в Ташкенте",
                        search_description="Zoo Planeta — сеть зоомагазинов в Ташкенте: корма, наполнители, "
                                           "аксессуары и ветаптека для собак, кошек, птиц, грызунов и рыб.")
        root.add_child(instance=home)
        self.publish(home)
        self.translate(home, "uz", seo_title="Zoo Planeta — Toshkentdagi zoodoʻkonlar tarmogʻi",
                       search_description="Zoo Planeta — Toshkentdagi zoodoʻkonlar tarmogʻi: itlar, mushuklar, "
                                          "qushlar, kemiruvchilar va baliqlar uchun yem, aksessuarlar va vetapteka.")
        self.translate(home, "en", seo_title="Zoo Planeta — pet store chain in Tashkent, Uzbekistan",
                       search_description="Zoo Planeta is a pet store chain in Tashkent, Uzbekistan: food, litter, "
                                          "accessories and veterinary products for dogs, cats, birds, rodents and fish.")
        return home

    def build_about(self, home):
        n = len(STORES)
        body = lambda i: [
            {"type": "text_image", "value": {
                "title": ("Сеть, которая растёт вместе с городом", "Shahar bilan birga oʻsayotgan tarmoq",
                          "A chain growing with the city")[i],
                "text": (rt(f"Zoo Planeta — это {n} зоомагазинов в разных районах Ташкента. Мы открываем магазины "
                            "у дома, чтобы корм, наполнитель или нужное средство всегда были рядом.",
                            "В каждом магазине одинаковые стандарты: проверенный ассортимент, контроль сроков "
                            "годности и продавцы, которые помогут с выбором."),
                         rt(f"Zoo Planeta — Toshkentning turli tumanlarida joylashgan {n} ta zoodoʻkon. Yem, "
                            "toʻldirgich yoki kerakli vosita doim yaqin boʻlishi uchun doʻkonlarni uy yonida ochamiz.",
                            "Har bir doʻkonda yagona standartlar: ishonchli assortiment, yaroqlilik muddati nazorati "
                            "va tanlashda yordam beradigan sotuvchilar."),
                         rt(f"Zoo Planeta operates {n} pet stores across the districts of Tashkent, Uzbekistan. "
                            "We open neighbourhood stores so that pet food and care products are always close to home.",
                            "Every store follows the same standards: a curated range, strict shelf-life control and "
                            "trained staff who help customers choose."))[i],
                "image": None, "image_left": False, "link": {"text": "", "page": None, "url": ""}}},
            {"type": "stats", "value": {"items": [
                {"value": str(n), "label": ("магазинов в Ташкенте", "ta doʻkon Toshkentda", "stores in Tashkent")[i]},
                {"value": str(len(DISTRICTS)), "label": ("районов города", "ta shahar tumani", "city districts")[i]},
                {"value": "7/7", "label": ("работаем без выходных", "dam olish kunlarisiz", "open every day")[i]},
                {"value": "8", "label": ("направлений ассортимента", "mahsulot yoʻnalishi", "product categories")[i]},
            ]}},
            {"type": "cards", "value": {
                "title": ("Наши принципы", "Bizning tamoyillarimiz", "Our principles")[i], "text": "",
                "columns": "3", "style": "numbered",
                "items": [
                    {"title": ("Свежесть", "Yangilik", "Freshness")[i],
                     "text": ("Сроки годности проверяются в каждом магазине ежедневно.",
                              "Yaroqlilik muddati har bir doʻkonda har kuni tekshiriladi.",
                              "Shelf life is checked in every store every day.")[i], "image": None, "page": None},
                    {"title": ("Доступность", "Qulaylik", "Convenience")[i],
                     "text": ("Магазины у дома и единые цены по всей сети.",
                              "Uy yonidagi doʻkonlar va butun tarmoqda yagona narxlar.",
                              "Neighbourhood stores and the same prices across the chain.")[i], "image": None, "page": None},
                    {"title": ("Забота", "Gʻamxoʻrlik", "Care")[i],
                     "text": ("Обучаем персонал, чтобы каждый покупатель получил верный совет.",
                              "Har bir xaridor toʻgʻri maslahat olishi uchun xodimlarni oʻqitamiz.",
                              "We train our staff so every customer gets the right advice.")[i], "image": None, "page": None},
                ]}},
        ]
        return self.tri(home, StandardPage, slug="about", show_in_menus=(True,) * 3,
                        title=("О компании", "Kompaniya haqida", "About us"),
                        intro=("Zoo Planeta — сеть зоомагазинов в Ташкенте.",
                               "Zoo Planeta — Toshkentdagi zoodoʻkonlar tarmogʻi.",
                               "Zoo Planeta is a pet store chain in Tashkent, Uzbekistan."),
                        body=(body(0), body(1), body(2)))

    def build_stores(self, home):
        index = self.tri(home, StoreIndexPage, slug="stores", show_in_menus=(True,) * 3,
                         title=("Магазины", "Doʻkonlar", "Stores"),
                         intro=("Адреса, часы работы и маршрут до ближайшего магазина.",
                                "Manzillar, ish vaqti va eng yaqin doʻkongacha yoʻnalish.",
                                "Addresses, opening hours and directions to the nearest store."))
        for k, (names, district, lat, lng, metro, h24) in enumerate(STORES, start=1):
            d = DISTRICTS[district]
            store = StorePage(
                title=names[0], slug=f"store-{k:02d}", locale=self.loc["ru"], district=d[0],
                address=f"{d[0]} р-н, {names[0]} (демо-адрес)", landmark="", metro=metro[0] if metro else "",
                phone=f"+998 71 200-10-{k:02d}", latitude=Decimal(str(lat)), longitude=Decimal(str(lng)),
                opens=dt.time(0, 0) if h24 else dt.time(9, 0), closes=dt.time(0, 0) if h24 else dt.time(22, 0),
                features=FEATURES[0] if k % 3 == 0 else "")
            self.add(index, store)
            self.translate(store, "uz", title=names[1], district=d[1], address=f"{d[1]} tumani, {names[1]} (demo manzil)",
                           metro=metro[1] if metro else "", features=FEATURES[1] if k % 3 == 0 else "")
            self.translate(store, "en", title=names[2], district=d[2], address=f"{names[2]}, {d[2]} district (demo address)",
                           metro=metro[2] if metro else "", features=FEATURES[2] if k % 3 == 0 else "")
        return index

    def build_promos(self, home):
        index = self.tri(home, PromoIndexPage, langs=("ru", "uz"), slug="promos", show_in_menus=(True, True),
                         title=("Акции", "Aksiyalar"),
                         intro=("Скидки и специальные предложения во всех магазинах сети.",
                                "Tarmoqning barcha doʻkonlarida chegirmalar va maxsus takliflar."))
        today = timezone.localdate()
        promos = [
            (("Сухие корма для кошек", "Mushuklar uchun quruq yem"), "−20%", 0, 14,
             ("Скидка на сухие корма популярных брендов.", "Mashhur brendlarning quruq yemlariga chegirma."), "", ""),
            (("Наполнители 1+1", "Toʻldirgichlar 1+1"), "1+1", -3, 10,
             ("Второй пакет наполнителя в подарок.", "Ikkinchi qop toʻldirgich sovgʻa."), "", ""),
            (("Лакомства для собак", "Itlar uchun shirinliklar"), "−15%", -1, 20,
             ("Жевательные лакомства и снеки со скидкой.", "Chaynaladigan shirinliklar va sneklar chegirmada."),
             "48 000 сум", "40 800 сум"),
            (("Всё для аквариума", "Akvarium uchun hammasi"), "−10%", -5, 25,
             ("Фильтры, грунт и корма для рыб.", "Filtrlar, grunt va baliq yemlari."), "", ""),
            (("Средства от блох и клещей", "Burga va kanaga qarshi vositalar"), "−25%", 7, 30,
             ("Подготовьте питомца к весне.", "Uy hayvoningizni bahorga tayyorlang."), "", ""),
            (("Новогодние подарки", "Yangi yil sovgʻalari"), "−30%", -60, -30,
             ("Праздничные наборы для питомцев.", "Uy hayvonlari uchun bayram toʻplamlari."), "", ""),
        ]
        terms = (rt("Акция действует во всех магазинах Zoo Planeta в указанные даты.") +
                 ul("Скидка не суммируется с другими предложениями.", "Количество товара ограничено."),
                 rt("Aksiya koʻrsatilgan sanalarda barcha Zoo Planeta doʻkonlarida amal qiladi.") +
                 ul("Chegirma boshqa takliflar bilan qoʻshilmaydi.", "Mahsulotlar soni cheklangan."))
        for k, (title, badge, start, end, summary, old, new) in enumerate(promos, start=1):
            self.tri(index, PromoPage, langs=("ru", "uz"), slug=f"promo-{k}",
                     title=title, summary=summary, body=terms,
                     badge=(badge, badge), old_price=(old, old.replace("сум", "soʻm")),
                     new_price=(new, new.replace("сум", "soʻm")),
                     date_from=(today + dt.timedelta(days=start),) * 2, date_to=(today + dt.timedelta(days=end),) * 2)
        return index

    def build_careers(self, home):
        body = lambda i: [
            {"type": "cards", "value": {
                "title": ("Почему у нас", "Nega aynan biz", "Why join us")[i], "text": "", "columns": "4", "style": "plain",
                "items": [
                    {"title": t[i], "text": d[i], "image": None, "page": None} for t, d in [
                        (("Официальное оформление", "Rasmiy ishga qabul", "Official employment"),
                         ("Трудовой договор и все отчисления.", "Mehnat shartnomasi va barcha toʻlovlar.",
                          "Employment contract and full social contributions.")),
                        (("Рядом с домом", "Uy yonida", "Close to home"),
                         (f"{len(STORES)} магазинов по всему Ташкенту.", f"Toshkent boʻylab {len(STORES)} ta doʻkon.",
                          f"{len(STORES)} stores all over Tashkent.")),
                        (("Обучение", "Oʻqitish", "Training"),
                         ("Научим всему о товарах и работе с покупателями.",
                          "Mahsulotlar va xaridorlar bilan ishlashni oʻrgatamiz.",
                          "We teach you about products and customer service.")),
                        (("Рост", "Oʻsish", "Growth"),
                         ("От продавца до управляющего магазином.", "Sotuvchidan doʻkon boshqaruvchisigacha.",
                          "From sales assistant to store manager.")),
                    ]]}},
        ]
        careers = self.tri(home, CareersPage, langs=("ru", "uz"), slug="careers", show_in_menus=(True, True),
                           title=("Карьера", "Karyera"),
                           intro=("Работа в сети зоомагазинов для тех, кто любит животных.",
                                  "Hayvonlarni sevadiganlar uchun zoodoʻkonlar tarmogʻida ish."),
                           body=(body(0), body(1)))
        vacancies = [
            (("Продавец-консультант", "Sotuvchi-maslahatchi"), "shift", ("2/2 по 12 часов", "2/2, 12 soatdan"),
             ("Магазины по всему Ташкенту", "Toshkent boʻylab doʻkonlar"), ("от 4 000 000 сум", "4 000 000 soʻmdan")),
            (("Кассир", "Kassir"), "shift", ("2/2 по 12 часов", "2/2, 12 soatdan"),
             ("Магазины по всему Ташкенту", "Toshkent boʻylab doʻkonlar"), ("от 3 800 000 сум", "3 800 000 soʻmdan")),
            (("Управляющий магазином", "Doʻkon boshqaruvchisi"), "full", ("5/2", "5/2"),
             ("Ташкент", "Toshkent"), ("от 7 000 000 сум", "7 000 000 soʻmdan")),
            (("Кладовщик", "Omborchi"), "full", ("6/1", "6/1"), ("Склад, Ташкент", "Ombor, Toshkent"),
             ("от 4 500 000 сум", "4 500 000 soʻmdan")),
        ]
        duties = (ul("Консультировать покупателей по товарам", "Следить за выкладкой и ценниками",
                     "Проверять сроки годности", "Работать с кассой"),
                  ul("Xaridorlarga mahsulotlar boʻyicha maslahat berish", "Mahsulot terilishi va narx yorliqlarini kuzatish",
                     "Yaroqlilik muddatini tekshirish", "Kassada ishlash"))
        reqs = (ul("Ответственность и вежливость", "Опыт в рознице — плюс", "Любовь к животным"),
                ul("Masʼuliyat va xushmuomalalik", "Chakana savdoda tajriba — afzallik", "Hayvonlarga mehr"))
        conds = (ul("Официальное оформление", "Стабильная зарплата два раза в месяц", "Обучение за счёт компании",
                    "Скидка сотрудника на товары"),
                 ul("Rasmiy ishga qabul", "Oyiga ikki marta barqaror maosh", "Kompaniya hisobidan oʻqitish",
                    "Xodimlar uchun chegirma"))
        for k, (title, emp, schedule, location, salary) in enumerate(vacancies, start=1):
            self.tri(careers, VacancyPage, langs=("ru", "uz"), slug=f"vacancy-{k}", title=title,
                     employment=(emp, emp), schedule=schedule, location=location, salary=salary,
                     summary=location, duties=duties, requirements=reqs, conditions=conds)
        return careers

    def build_partners(self, home):
        body = lambda i: [
            {"type": "cards", "value": {
                "title": ("Направления сотрудничества", "Hamkorlik yoʻnalishlari", "How we work with partners")[i],
                "text": "", "columns": "2", "style": "plain",
                "items": [
                    {"title": t[i], "text": d[i], "image": None, "page": None} for t, d in [
                        (("Поставщикам и дистрибьюторам", "Yetkazib beruvchilar va distribyutorlarga",
                          "Suppliers and distributors"),
                         ("Рассматриваем корма, наполнители, аксессуары и ветеринарные товары для всей сети.",
                          "Butun tarmoq uchun yem, toʻldirgich, aksessuar va veterinariya mahsulotlarini koʻrib chiqamiz.",
                          "We list pet food, litter, accessories and veterinary products across the whole chain.")),
                        (("Производителям и брендам", "Ishlab chiqaruvchilar va brendlarga", "Manufacturers and brands"),
                         ("Вывод нового бренда на рынок Узбекистана: эксклюзивная дистрибуция, промо в магазинах.",
                          "Yangi brendni Oʻzbekiston bozoriga olib chiqish: eksklyuziv distribyutsiya, doʻkonlarda promo.",
                          "Bring your brand to the Uzbekistan market: exclusive distribution and in-store promotion.")),
                        (("Арендодателям", "Ijaraga beruvchilarga", "Landlords"),
                         ("Ищем помещения 60–200 м² на первых этажах в жилых районах Ташкента.",
                          "Toshkentning turar-joy hududlarida birinchi qavatda 60–200 m² binolar izlaymiz.",
                          "We are looking for 60–200 m² ground-floor premises in residential areas of Tashkent.")),
                        (("Рекламным партнёрам", "Reklama hamkorlariga", "Marketing partners"),
                         ("Совместные акции, размещение в магазинах и наших соцсетях.",
                          "Qoʻshma aksiyalar, doʻkonlarda va ijtimoiy tarmoqlarimizda joylashtirish.",
                          "Joint campaigns, in-store placement and our social media.")),
                    ]]}},
            {"type": "stats", "value": {"items": [
                {"value": str(len(STORES)), "label": ("магазинов в Ташкенте", "ta doʻkon Toshkentda", "stores in Tashkent")[i]},
                {"value": str(len(DISTRICTS)), "label": ("районов присутствия", "ta tumanda", "city districts covered")[i]},
                {"value": "7/7", "label": ("работаем ежедневно", "har kuni ishlaymiz", "open every day")[i]},
            ]}},
            {"type": "logos", "value": {"title": ("Бренды в наших магазинах", "Doʻkonlarimizdagi brendlar",
                                                  "Brands in our stores")[i], "names": BRANDS, "logos": []}},
        ]
        return self.tri(home, PartnersPage, slug="partners", show_in_menus=(True,) * 3,
                        title=("Партнёрам", "Hamkorlarga", "Partners"),
                        intro=("Сотрудничество с сетью зоомагазинов Zoo Planeta: поставки, дистрибуция брендов, аренда.",
                               "Zoo Planeta zoodoʻkonlar tarmogʻi bilan hamkorlik: yetkazib berish, brend distribyutsiyasi, ijara.",
                               "Partner with Zoo Planeta, a pet retail chain in Tashkent: supply, brand distribution, retail premises."),
                        form_intro=("Опишите предложение — менеджер ответит в течение 3 рабочих дней.",
                                    "Taklifingizni yozing — menejer 3 ish kuni ichida javob beradi.",
                                    "Tell us about your proposal — our manager will reply within 3 business days."),
                        body=(body(0), body(1), body(2)))

    def build_contacts(self, home):
        return self.tri(home, ContactPage, slug="contacts", show_in_menus=(True,) * 3,
                        title=("Контакты", "Aloqa", "Contacts"),
                        intro=("Справочная, адреса магазинов и обратная связь.",
                               "Maʼlumot xizmati, doʻkonlar manzillari va fikr-mulohaza.",
                               "Customer line, store addresses and feedback."))

    def build_news(self, home):
        index = self.tri(home, NewsIndexPage, langs=("ru", "uz"), slug="news", title=("Новости", "Yangiliklar"),
                         intro=("События и новости сети Zoo Planeta.", "Zoo Planeta tarmogʻi yangiliklari."))
        today = timezone.localdate()
        news = [
            (("Открыли новый магазин в Сергели", "Sergelida yangi doʻkon ochildi"), 3,
             ("Ещё один магазин Zoo Planeta теперь работает в Сергелийском районе.",
              "Sergeli tumanida yana bir Zoo Planeta doʻkoni ishga tushdi.")),
            (("Как выбрать корм для котёнка", "Mushukcha uchun yemni qanday tanlash kerak"), 12,
             ("Советы наших консультантов: на что смотреть на упаковке.",
              "Maslahatchilarimiz tavsiyalari: qadoqda nimaga eʼtibor berish kerak.")),
            (("Zoo Planeta поддержала приют для животных", "Zoo Planeta hayvonlar boshpanasini qoʻllab-quvvatladi"), 25,
             ("Передали корма и наполнители в городской приют.", "Shahar boshpanasiga yem va toʻldirgichlar topshirildi.")),
        ]
        for k, (title, ago, summary) in enumerate(news, start=1):
            self.tri(index, NewsPage, langs=("ru", "uz"), slug=f"news-{k}", title=title, summary=summary,
                     date=(today - dt.timedelta(days=ago),) * 2,
                     body=([{"type": "text", "value": rt(summary[0], "Демо-текст новости — замените в CMS.")}],
                           [{"type": "text", "value": rt(summary[1], "Demo matn — CMS orqali almashtiring.")}]))
        return index

    def build_privacy(self, home):
        text = ("Здесь будет политика обработки персональных данных. Текст должен подготовить юрист компании.",
                "Bu yerda shaxsiy maʼlumotlarni qayta ishlash siyosati boʻladi. Matnni kompaniya yuristi tayyorlashi kerak.",
                "The personal data policy goes here. It should be prepared by the company's lawyer.")
        return self.tri(home, StandardPage, slug="privacy",
                        title=("Политика конфиденциальности", "Maxfiylik siyosati", "Privacy policy"),
                        intro=("", "", ""), body=tuple([{"type": "text", "value": rt(t)}] for t in text))

    def fill_home(self, home, about, stores, promos, careers, partners):
        def slides(i, code):
            items = [
                {"type": "slide", "value": {
                    "title": ("Всё для питомцев — рядом с домом", "Uy hayvonlari uchun hammasi — uyingiz yonida",
                              "Everything for pets, close to home")[i],
                    "text": (f"{len(STORES)} магазинов Zoo Planeta в Ташкенте. Корма, наполнители, аксессуары и ветаптека.",
                             f"Toshkentda {len(STORES)} ta Zoo Planeta doʻkoni. Yem, toʻldirgich, aksessuarlar va vetapteka.",
                             f"{len(STORES)} Zoo Planeta stores in Tashkent: pet food, litter, accessories and vet care.")[i],
                    "image": None, "theme": "yellow",
                    "link": {"text": ("Найти магазин", "Doʻkon topish", "Find a store")[i],
                             "page": stores.get_translation(self.loc[code]).pk, "url": ""}}},
            ]
            if code != "en":
                items.append({"type": "slide", "value": {
                    "title": ("−20% на сухие корма для кошек", "Mushuklar uchun quruq yemga −20%")[i],
                    "text": ("Две недели во всех магазинах сети.", "Ikki hafta davomida barcha doʻkonlarda.")[i],
                    "image": None, "theme": "dark",
                    "link": {"text": ("Все акции", "Barcha aksiyalar")[i],
                             "page": promos.get_translation(self.loc[code]).pk, "url": ""}}})
                items.append({"type": "slide", "value": {
                    "title": ("Ищем продавцов-консультантов", "Sotuvchi-maslahatchilar kerak")[i],
                    "text": ("Работа рядом с домом, обучение и стабильная зарплата.",
                             "Uy yonida ish, oʻqitish va barqaror maosh.")[i],
                    "image": None, "theme": "light",
                    "link": {"text": ("Вакансии", "Vakansiyalar")[i],
                             "page": careers.get_translation(self.loc[code]).pk, "url": ""}}})
            else:
                items.append({"type": "slide", "value": {
                    "title": "Partner with a growing pet retail chain",
                    "text": "Supply, brand distribution and retail premises in Tashkent.",
                    "image": None, "theme": "dark",
                    "link": {"text": "Become a partner", "page": partners.get_translation(self.loc["en"]).pk, "url": ""}}})
            return items

        cats = [
            (("Собаки", "Itlar", "Dogs"), ("Корма, лакомства, амуниция", "Yem, shirinliklar, anjomlar", "Food, treats, leads")),
            (("Кошки", "Mushuklar", "Cats"), ("Корма, наполнители, когтеточки", "Yem, toʻldirgich, tirnoqcharx", "Food, litter, scratchers")),
            (("Грызуны", "Kemiruvchilar", "Small pets"), ("Корма, сено, клетки", "Yem, pichan, kataklar", "Food, hay, cages")),
            (("Птицы", "Qushlar", "Birds"), ("Зерновые смеси, клетки", "Don aralashmalari, kataklar", "Seed mixes, cages")),
            (("Аквариумистика", "Akvariumistika", "Aquatics"), ("Аквариумы, фильтры, корма", "Akvarium, filtr, yem", "Tanks, filters, fish food")),
            (("Ветаптека", "Vetapteka", "Vet pharmacy"), ("От блох и клещей, витамины", "Burga va kanaga qarshi, vitaminlar", "Flea & tick, vitamins")),
            (("Уход и гигиена", "Parvarish va gigiena", "Grooming"), ("Шампуни, пелёнки, расчёски", "Shampun, taglik, taroq", "Shampoos, pads, brushes")),
            (("Аксессуары", "Aksessuarlar", "Accessories"), ("Миски, лежанки, переноски", "Idish, toʻshak, tashish qutisi", "Bowls, beds, carriers")),
        ]

        def body(i, code):
            blocks = [
                {"type": "categories", "value": {
                    "title": ("Что есть в наших магазинах", "Doʻkonlarimizda nimalar bor", "What we sell")[i],
                    "text": ("Наличие конкретного товара уточняйте в магазине.", "Aniq mahsulot borligini doʻkondan soʻrang.",
                             "Product availability varies by store.")[i],
                    "items": [{"title": t[i], "text": d[i], "image": None} for t, d in cats]}},
                {"type": "text_image", "value": {
                    "title": ("Zoo Planeta — зоомагазин в вашем районе", "Zoo Planeta — mahallangizdagi zoodoʻkon",
                              "Zoo Planeta — the pet store next door")[i],
                    "text": (rt("Мы открываем магазины у дома и держим одинаковые стандарты во всей сети: проверенный "
                                "ассортимент, контроль сроков годности и внимательные консультанты."),
                             rt("Doʻkonlarni uy yonida ochamiz va butun tarmoqda yagona standartlarni saqlaymiz: "
                                "ishonchli assortiment, yaroqlilik muddati nazorati va eʼtiborli maslahatchilar."),
                             rt("We open neighbourhood stores and keep one standard across the chain: a curated range, "
                                "strict shelf-life control and helpful staff."))[i],
                    "image": None, "image_left": True,
                    "link": {"text": ("О компании", "Kompaniya haqida", "About us")[i],
                             "page": about.get_translation(self.loc[code]).pk, "url": ""}}},
                {"type": "logos", "value": {"title": ("Бренды", "Brendlar", "Brands")[i], "names": BRANDS, "logos": []}},
            ]
            if code != "en":
                blocks.append({"type": "cta", "value": {
                    "title": ("Работа в Zoo Planeta", "Zoo Planetada ish")[i],
                    "text": ("Ищем продавцов, кассиров и управляющих. Официальное оформление и обучение.",
                             "Sotuvchi, kassir va boshqaruvchilarni izlaymiz. Rasmiy ishga qabul va oʻqitish.")[i],
                    "theme": "yellow",
                    "link": {"text": ("Смотреть вакансии", "Vakansiyalarni koʻrish")[i],
                             "page": careers.get_translation(self.loc[code]).pk, "url": ""}}})
            else:
                blocks.append({"type": "cta", "value": {
                    "title": "Looking for a retail partner in Uzbekistan?",
                    "text": "We work with manufacturers and distributors of pet food and accessories.",
                    "theme": "dark",
                    "link": {"text": "Partnership request", "page": partners.get_translation(self.loc["en"]).pk, "url": ""}}})
            return blocks

        for i, code in enumerate(L):
            page = home.get_translation(self.loc[code]).specific
            page.slides = slides(i, code)
            page.body = body(i, code)
            page.save()
            self.publish(page)
