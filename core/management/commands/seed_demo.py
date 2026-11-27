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

from catalog.models import Brand, CategoryIndexPage, CategoryPage
from core.models import SiteSettings
from pages.models import (CareersPage, CharityIndexPage, CharityPage, ContactPage, DeliveryPage, HomePage, LoyaltyPage,
                          NewsIndexPage, NewsPage, PartnersPage, PromoIndexPage, PromoPage, StandardPage, VacancyPage)
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


# slug, icon, title, summary, subcategories (ru/uz/en), brands
CATEGORIES = [
    ("dogs", "dog", ("Для собак", "Itlar uchun", "Dogs"),
     ("Корма, лакомства, амуниция и лежанки", "Yem, shirinliklar, anjom va toʻshaklar", "Food, treats, leads and beds"),
     ("Сухие корма, Влажные корма, Лакомства, Ошейники и поводки, Лежанки, Одежда",
      "Quruq yem, Hoʻl yem, Shirinliklar, Boʻyinbogʻ va tasmalar, Toʻshaklar, Kiyimlar",
      "Dry food, Wet food, Treats, Collars and leads, Beds, Clothing"),
     ["Royal Canin", "Purina Pro Plan", "Hill's", "Brit", "Acana", "Pedigree", "Trixie"]),
    ("cats", "cat", ("Для кошек", "Mushuklar uchun", "Cats"),
     ("Корма, наполнители, когтеточки и игрушки", "Yem, toʻldirgich, tirnoqcharx va oʻyinchoqlar",
      "Food, litter, scratchers and toys"),
     ("Сухие корма, Влажные корма, Наполнители, Лотки, Когтеточки, Игрушки",
      "Quruq yem, Hoʻl yem, Toʻldirgichlar, Tovoqlar, Tirnoqcharxlar, Oʻyinchoqlar",
      "Dry food, Wet food, Litter, Litter boxes, Scratchers, Toys"),
     ["Royal Canin", "Purina Pro Plan", "Hill's", "Brit", "Monge", "Whiskas"]),
    ("birds", "bird", ("Для птиц", "Qushlar uchun", "Birds"),
     ("Зерновые смеси, клетки и аксессуары", "Don aralashmalari, kataklar va aksessuarlar", "Seed mixes, cages, accessories"),
     ("Зерновые смеси, Лакомства, Клетки, Поилки и кормушки, Минералы",
      "Don aralashmalari, Shirinliklar, Kataklar, Suv va yem idishlari, Minerallar",
      "Seed mixes, Treats, Cages, Feeders, Minerals"),
     ["Vitakraft", "Trixie"]),
    ("rodents", "rodent", ("Для грызунов", "Kemiruvchilar uchun", "Small pets"),
     ("Корма, сено, клетки и наполнители", "Yem, pichan, kataklar va toʻldirgichlar", "Food, hay, cages and bedding"),
     ("Корма, Сено, Клетки, Наполнители, Домики, Лакомства",
      "Yem, Pichan, Kataklar, Toʻldirgichlar, Uychalar, Shirinliklar",
      "Food, Hay, Cages, Bedding, Houses, Treats"),
     ["Vitakraft", "Trixie"]),
    ("aquatics", "fish", ("Аквариумистика", "Akvariumistika", "Aquatics"),
     ("Аквариумы, фильтры, корма для рыб", "Akvarium, filtr, baliq yemi", "Tanks, filters and fish food"),
     ("Аквариумы, Фильтры и компрессоры, Корма для рыб, Грунт и декор, Химия для воды",
      "Akvariumlar, Filtr va kompressorlar, Baliq yemi, Grunt va dekor, Suv uchun kimyo",
      "Aquariums, Filters and pumps, Fish food, Gravel and decor, Water care"),
     ["Tetra"]),
    ("vet", "vet", ("Ветеринарные товары", "Veterinariya mahsulotlari", "Vet products"),
     ("Средства от блох и клещей, витамины", "Burga va kanaga qarshi vositalar, vitaminlar", "Flea and tick, vitamins"),
     ("От блох и клещей, Витамины, Глистогонные, Уход за глазами и ушами",
      "Burga va kanaga qarshi, Vitaminlar, Gijjaga qarshi, Koʻz va quloq parvarishi",
      "Flea and tick, Vitamins, Dewormers, Eye and ear care"),
     ["Hill's", "Royal Canin"]),
    ("accessories", "bowl", ("Аксессуары", "Aksessuarlar", "Accessories"),
     ("Миски, переноски, лежанки, амуниция", "Idishlar, tashish qutilari, toʻshaklar", "Bowls, carriers, beds"),
     ("Миски, Переноски, Лежанки, Груминг, Пелёнки, Шампуни",
      "Idishlar, Tashish qutilari, Toʻshaklar, Gruming, Tagliklar, Shampunlar",
      "Bowls, Carriers, Beds, Grooming, Pads, Shampoos"),
     ["Trixie"]),
    ("toys", "toy", ("Игрушки", "Oʻyinchoqlar", "Toys"),
     ("Для игр, тренировок и жевания", "Oʻyin, mashq va kemirish uchun", "For play, training and chewing"),
     ("Мячи, Канаты, Дразнилки, Интерактивные игрушки, Жевательные игрушки",
      "Toʻplar, Arqonlar, Qiziqtirgichlar, Interaktiv oʻyinchoqlar, Kemiriladigan oʻyinchoqlar",
      "Balls, Ropes, Teasers, Interactive toys, Chew toys"),
     ["Trixie"]),
]


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

        # creation order = menu order
        about = self.build_about(home)
        stores = self.build_stores(home)
        self.build_catalog(home)
        promos = self.build_promos(home)
        self.build_news(home)
        self.build_charity(home)
        delivery = self.build_delivery(home)
        self.build_loyalty(home)
        careers = self.build_careers(home)
        partners = self.build_partners(home)
        self.build_contacts(home)
        privacy = self.build_privacy(home)
        settings = SiteSettings.load()
        settings.privacy_page = privacy
        settings.save()
        self.fill_home(home, about, stores, promos, careers, partners, delivery)
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
            {"type": "stores_map", "value": {
                "title": ("География сети", "Tarmoq geografiyasi", "Where we are")[i],
                "text": ("Магазины Zoo Planeta работают во всех крупных районах Ташкента.",
                         "Zoo Planeta doʻkonlari Toshkentning barcha yirik tumanlarida ishlaydi.",
                         "Zoo Planeta stores operate in every major district of Tashkent.")[i]}},
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
        careers = self.tri(home, CareersPage, langs=("ru", "uz"), slug="careers", show_in_menus=(False, False),
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
        return self.tri(home, PartnersPage, slug="partners", show_in_menus=(False, False, True),
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
        index = self.tri(home, NewsIndexPage, langs=("ru", "uz"), slug="news", show_in_menus=(True, True), title=("Новости", "Yangiliklar"),
                         intro=("События и новости сети Zoo Planeta.", "Zoo Planeta tarmogʻi yangiliklari."))
        today = timezone.localdate()
        news = [
            (("Открыли новый магазин в Сергели", "Sergelida yangi doʻkon ochildi"), 3, "opening",
             ("Ещё один магазин Zoo Planeta теперь работает в Сергелийском районе.",
              "Sergeli tumanida yana bir Zoo Planeta doʻkoni ishga tushdi.")),
            (("Как выбрать корм для котёнка", "Mushukcha uchun yemni qanday tanlash kerak"), 12, "vet",
             ("Советы наших консультантов: на что смотреть на упаковке.",
              "Maslahatchilarimiz tavsiyalari: qadoqda nimaga eʼtibor berish kerak.")),
            (("Zoo Planeta поддержала приют для животных", "Zoo Planeta hayvonlar boshpanasini qoʻllab-quvvatladi"), 25, "event",
             ("Передали корма и наполнители в городской приют.", "Shahar boshpanasiga yem va toʻldirgichlar topshirildi.")),
        ]
        news.append((("Зимний уход за лапами собаки", "Qishda it panjalarini parvarishlash"), 40, "care",
                     ("Реагенты и холод: как защитить лапы на прогулке.",
                      "Reagentlar va sovuq: sayrda panjalarni qanday himoya qilish kerak.")))
        for k, (title, ago, kind, summary) in enumerate(news, start=1):
            self.tri(index, NewsPage, langs=("ru", "uz"), slug=f"news-{k}", title=title, summary=summary,
                     kind=(kind, kind),
                     date=(today - dt.timedelta(days=ago),) * 2,
                     body=([{"type": "text", "value": rt(summary[0], "Демо-текст новости — замените в CMS.")}],
                           [{"type": "text", "value": rt(summary[1], "Demo matn — CMS orqali almashtiring.")}]))
        return index

    def build_catalog(self, home):
        index = self.tri(home, CategoryIndexPage, slug="catalog", show_in_menus=(True,) * 3,
                         title=("Каталог", "Katalog", "Catalogue"),
                         intro=("Основные направления ассортимента Zoo Planeta. Сайт информационный — купить товар можно "
                                "в любом из наших магазинов.",
                                "Zoo Planeta assortimentining asosiy yoʻnalishlari. Sayt maʼlumot uchun — mahsulotni "
                                "istalgan doʻkonimizdan xarid qilishingiz mumkin.",
                                "The main product categories at Zoo Planeta stores."),
                         note=("", "", ""))
        brands = {}
        for k, name in enumerate(BRANDS):
            brands[name] = Brand.objects.get_or_create(name=name, defaults={"sort_order": k * 10})[0]
        for k, (slug, icon, titles, summaries, subs, brand_names) in enumerate(CATEGORIES, start=1):
            page = self.tri(index, CategoryPage, slug=slug, icon=(icon,) * 3, title=titles, summary=summaries,
                            subcategories=subs)
            for p in [page, *page.get_translations()]:
                p = p.specific
                p.brands.set([brands[b] for b in brand_names if b in brands])
                p.save()
                self.publish(p)
        return index

    def build_charity(self, home):
        n = len(STORES)
        index = self.tri(
            home, CharityIndexPage, langs=("ru", "uz"), slug="give-a-paw", show_in_menus=(True, True),
            title=("Give a Paw", "Give a Paw"),
            intro=("Социальная программа Zoo Planeta: помогаем приютам и бездомным животным и объединяем людей, "
                   "которым не всё равно.",
                   "Zoo Planeta ijtimoiy dasturi: boshpanalar va uysiz hayvonlarga yordam beramiz hamda befarq "
                   "boʻlmagan insonlarni birlashtiramiz."),
            donate_text=("", ""), donate_url=("", ""),
            body=([{"type": "stats", "value": {"items": [
                       {"value": "4", "label": "приюта-партнёра"}, {"value": "2,5 т", "label": "корма передано за год"},
                       {"value": str(n), "label": "пунктов сбора помощи в магазинах"}]}},
                   {"type": "text", "value": rt(
                       "В каждом магазине Zoo Planeta стоит корзина Give a Paw: покупатели оставляют в ней корм, "
                       "наполнитель и игрушки, а мы раз в месяц передаём собранное приютам-партнёрам.",
                       "Демо-текст — замените в CMS.")}],
                  [{"type": "stats", "value": {"items": [
                       {"value": "4", "label": "hamkor boshpana"}, {"value": "2,5 t", "label": "yil davomida topshirilgan yem"},
                       {"value": str(n), "label": "doʻkonlarda yordam yigʻish nuqtasi"}]}},
                   {"type": "text", "value": rt(
                       "Har bir Zoo Planeta doʻkonida Give a Paw savati bor: xaridorlar unga yem, toʻldirgich va "
                       "oʻyinchoqlar qoldiradi, biz esa oyiga bir marta yigʻilganini hamkor boshpanalarga topshiramiz.",
                       "Demo matn — CMS orqali almashtiring.")}]))
        today = timezone.localdate()
        items = [
            ("project", "", 30, ("Корзина добра в каждом магазине", "Har bir doʻkonda ezgulik savati"),
             ("Оставьте корм для приюта — мы доставим.", "Boshpana uchun yem qoldiring — biz yetkazamiz.")),
            ("event", "", 14, ("День открытых дверей в приюте", "Boshpanada ochiq eshiklar kuni"),
             ("Волонтёры Zoo Planeta провели день в городском приюте.",
              "Zoo Planeta koʻngillilari shahar boshpanasida bir kun oʻtkazishdi.")),
            ("story", "looking", 5, ("Рыжик ищет дом", "Ryjik uy izlamoqda"),
             ("Ласковый кот, 2 года, привит и стерилизован.", "Mehribon mushuk, 2 yosh, emlangan va sterilizatsiya qilingan.")),
            ("story", "home", 21, ("Белка нашла семью", "Belka oila topdi"),
             ("Собака из приюта-партнёра теперь живёт в Юнусабаде.",
              "Hamkor boshpanadagi it endi Yunusobodda yashaydi.")),
        ]
        for k, (kind, status, ago, title, summary) in enumerate(items, start=1):
            self.tri(index, CharityPage, langs=("ru", "uz"), slug=f"gap-{k}", title=title, summary=summary,
                     kind=(kind, kind), animal_status=(status, status), date=(today - dt.timedelta(days=ago),) * 2,
                     body=([{"type": "text", "value": rt(summary[0], "Демо-текст — замените в CMS.")}],
                           [{"type": "text", "value": rt(summary[1], "Demo matn — CMS orqali almashtiring.")}]))
        return index

    def build_delivery(self, home):
        def adv(icon, t, d):
            return {"type": "item", "value": {"icon": icon, "title": t, "text": d}}

        def step(t, d):
            return {"type": "step", "value": {"title": t, "text": d}}

        def svc(name, note):
            return {"type": "service", "value": {"name": name, "logo": None, "url": "", "note": note}}

        return self.tri(
            home, DeliveryPage, langs=("ru", "uz"), slug="delivery", show_in_menus=(False, False),
            title=("Доставка", "Yetkazib berish"),
            intro=("Корма, наполнители и товары для питомцев с доставкой по Ташкенту — в нашем приложении "
                   "и в популярных сервисах доставки.",
                   "Yem, toʻldirgich va uy hayvonlari uchun mahsulotlar Toshkent boʻylab yetkazib beriladi — "
                   "ilovamizda va mashhur yetkazib berish xizmatlarida."),
            app_title=("Приложение Zoo Planeta", "Zoo Planeta ilovasi"),
            app_text=("Весь ассортимент ближайшего магазина в телефоне: цены, акции и доставка домой.",
                      "Eng yaqin doʻkonning butun assortimenti telefoningizda: narxlar, aksiyalar va uyga yetkazish."),
            app_features=([adv("tag", "Цены и акции", "Те же цены, что в магазине, и скидки только для приложения."),
                           adv("clock", "Быстрая доставка", "Привезём из ближайшего магазина в удобное время."),
                           adv("gift", "Бонусы UDS", "Баллы начисляются и за заказы в приложении.")],
                          [adv("tag", "Narxlar va aksiyalar", "Doʻkondagi narxlar va faqat ilova uchun chegirmalar."),
                           adv("clock", "Tez yetkazish", "Eng yaqin doʻkondan qulay vaqtda olib kelamiz."),
                           adv("gift", "UDS bonuslari", "Ilovadagi buyurtmalar uchun ham ball beriladi.")]),
            screenshots=([], []),
            steps=([step("Скачайте приложение", "App Store или Google Play."),
                    step("Выберите товары", "Ассортимент ближайшего к вам магазина."),
                    step("Получите заказ", "Курьер привезёт его в выбранное время.")],
                   [step("Ilovani yuklab oling", "App Store yoki Google Play."),
                    step("Mahsulotlarni tanlang", "Sizga eng yaqin doʻkon assortimenti."),
                    step("Buyurtmani oling", "Kuryer tanlangan vaqtda olib keladi.")]),
            conditions=(ul("Зона доставки: весь Ташкент (демо-текст).", "Минимальная сумма заказа — уточните в приложении.",
                           "Оплата: картой в приложении или курьеру."),
                        ul("Yetkazish hududi: butun Toshkent (demo matn).", "Minimal buyurtma summasi — ilovada.",
                           "Toʻlov: ilovada karta orqali yoki kuryerga.")),
            aggregators=([svc("Express24", "Демо — укажите ссылку в CMS"), svc("Yandex Eats", "Демо — укажите ссылку в CMS"),
                          svc("Uzum Tezkor", "Демо — укажите ссылку в CMS")],
                         [svc("Express24", "Demo — CMS’da havolani kiriting"), svc("Yandex Eats", "Demo — CMS’da havolani kiriting"),
                          svc("Uzum Tezkor", "Demo — CMS’da havolani kiriting")]),
            body=([], []))

    def build_loyalty(self, home):
        def step(t, d):
            return {"type": "step", "value": {"title": t, "text": d}}

        return self.tri(
            home, LoyaltyPage, langs=("ru", "uz"), slug="bonus", show_in_menus=(False, False),
            title=("Бонусы UDS", "UDS bonuslari"),
            intro=("Программа лояльности Zoo Planeta в приложении UDS: баллы с каждой покупки во всех магазинах сети.",
                   "UDS ilovasidagi Zoo Planeta sodiqlik dasturi: tarmoqning barcha doʻkonlarida har bir xariddan ball."),
            cashback=("до 5%", "5% gacha"),
            cashback_note=("баллами с каждой покупки (демо)", "har bir xariddan ball (demo)"),
            steps=([step("Установите UDS", "Бесплатное приложение в App Store или Google Play."),
                    step("Вступите в Zoo Planeta", "По ссылке или промокоду на этой странице."),
                    step("Покажите код на кассе", "Баллы начислятся автоматически — ими можно оплатить часть покупки.")],
                   [step("UDS ni oʻrnating", "App Store yoki Google Play’dagi bepul ilova."),
                    step("Zoo Planetaga qoʻshiling", "Shu sahifadagi havola yoki promokod orqali."),
                    step("Kassada kodni koʻrsating", "Ballar avtomatik yoziladi — ular bilan xaridning bir qismini toʻlash mumkin.")]),
            rules=(rt("Демо-текст. Укажите процент кешбэка, какую часть покупки можно оплатить баллами и срок их действия."),
                   rt("Demo matn. Keshbek foizi, xaridning qancha qismini ball bilan toʻlash mumkinligi va amal qilish muddatini yozing.")),
            body=([], []))

    def build_privacy(self, home):
        text = ("Здесь будет политика обработки персональных данных. Текст должен подготовить юрист компании.",
                "Bu yerda shaxsiy maʼlumotlarni qayta ishlash siyosati boʻladi. Matnni kompaniya yuristi tayyorlashi kerak.",
                "The personal data policy goes here. It should be prepared by the company's lawyer.")
        return self.tri(home, StandardPage, slug="privacy",
                        title=("Политика конфиденциальности", "Maxfiylik siyosati", "Privacy policy"),
                        intro=("", "", ""), body=tuple([{"type": "text", "value": rt(t)}] for t in text))

    def fill_home(self, home, about, stores, promos, careers, partners, delivery):
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
                    "title": ("Доставка корма домой", "Yemni uyga yetkazib beramiz")[i],
                    "text": ("Закажите в приложении Zoo Planeta или в сервисах доставки.",
                             "Zoo Planeta ilovasida yoki yetkazib berish xizmatlarida buyurtma bering.")[i],
                    "image": None, "theme": "light",
                    "link": {"text": ("Заказать доставку", "Buyurtma berish")[i],
                             "page": delivery.get_translation(self.loc[code]).pk, "url": ""}}})
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

        def body(i, code):
            if code != "en":
                return [{"type": "cta", "value": {
                    "title": ("Работа в Zoo Planeta", "Zoo Planetada ish")[i],
                    "text": ("Ищем продавцов, кассиров и управляющих. Официальное оформление и обучение.",
                             "Sotuvchi, kassir va boshqaruvchilarni izlaymiz. Rasmiy ishga qabul va oʻqitish.")[i],
                    "theme": "dark",
                    "link": {"text": ("Смотреть вакансии", "Vakansiyalarni koʻrish")[i],
                             "page": careers.get_translation(self.loc[code]).pk, "url": ""}}}]
            return [{"type": "cta", "value": {
                "title": "Looking for a retail partner in Uzbekistan?",
                "text": "We work with manufacturers and distributors of pet food and accessories.",
                "theme": "dark",
                "link": {"text": "Partnership request", "page": partners.get_translation(self.loc["en"]).pk, "url": ""}}}]

        n = len(STORES)
        intro = {
            "intro_title": ("Крупная сеть зоомагазинов Ташкента", "Toshkentdagi yirik zoodoʻkonlar tarmogʻi",
                            "A leading pet retail chain in Tashkent"),
            "intro_text": ("Zoo Planeta объединяет магазины у дома, проверенных поставщиков и людей, которые любят "
                           "животных. Единые стандарты качества и сервиса — в каждом филиале.",
                           "Zoo Planeta uy yonidagi doʻkonlar, ishonchli yetkazib beruvchilar va hayvonlarni sevuvchi "
                           "insonlarni birlashtiradi. Har bir filialda yagona sifat va xizmat standartlari.",
                           "Zoo Planeta brings together neighbourhood stores, trusted suppliers and people who love "
                           "animals, with one standard of quality and service in every branch."),
            "about_title": ("Zoo Planeta — зоомагазин в вашем районе", "Zoo Planeta — mahallangizdagi zoodoʻkon",
                            "Zoo Planeta — the pet store next door"),
            "about_text": (rt("Мы открываем магазины у дома и держим одинаковые стандарты во всей сети: проверенный "
                              "ассортимент, контроль сроков годности и внимательные консультанты."),
                           rt("Doʻkonlarni uy yonida ochamiz va butun tarmoqda yagona standartlarni saqlaymiz: "
                              "ishonchli assortiment, yaroqlilik muddati nazorati va eʼtiborli maslahatchilar."),
                           rt("We open neighbourhood stores and keep one standard across the chain: a curated range, "
                              "strict shelf-life control and helpful staff.")),
        }
        stats = [("{stores}", ("магазинов в Ташкенте", "ta doʻkon Toshkentda", "stores in Tashkent")),
                 (str(len(DISTRICTS)), ("районов города", "ta shahar tumani", "city districts")),
                 ("3 000+", ("товаров в ассортименте", "dan ortiq mahsulot", "products in range")),
                 ("7/7", ("работаем без выходных", "dam olish kunlarisiz", "open every day"))]
        advantages = [
            ("store", ("Рядом с домом", "Uyingiz yonida", "Close to home"),
             (f"{n} магазинов в разных районах города.", f"Shaharning turli tumanlarida {n} ta doʻkon.",
              f"{n} stores across the city.")),
            ("check", ("Проверенный ассортимент", "Ishonchli assortiment", "Trusted range"),
             ("Работаем напрямую с производителями и официальными дистрибьюторами.",
              "Ishlab chiqaruvchilar va rasmiy distribyutorlar bilan bevosita ishlaymiz.",
              "We work directly with manufacturers and official distributors.")),
            ("tag", ("Честные цены", "Halol narxlar", "Fair prices"),
             ("Единые цены во всей сети и регулярные акции.", "Butun tarmoqda yagona narxlar va doimiy aksiyalar.",
              "The same prices chain-wide and regular offers.")),
            ("paw", ("Забота о животных", "Hayvonlarga gʻamxoʻrlik", "We care"),
             ("Консультанты помогут с выбором, а программа Give a Paw — приютам.",
              "Maslahatchilar tanlashda yordam beradi, Give a Paw esa boshpanalarga.",
              "Staff help you choose, and Give a Paw supports shelters.")),
        ]

        for i, code in enumerate(L):
            page = home.get_translation(self.loc[code]).specific
            page.slides = slides(i, code)
            page.body = body(i, code)
            for field, values in intro.items():
                setattr(page, field, values[i])
            page.stats = [{"type": "stat", "value": {"value": v, "label": label[i]}} for v, label in stats]
            page.advantages = [{"type": "item", "value": {"icon": ic, "title": t[i], "text": d[i]}}
                               for ic, t, d in advantages]
            page.about_page = about.get_translation(self.loc[code])
            page.save()
            self.publish(page)
