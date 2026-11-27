"""StreamField blocks the editors combine into pages."""
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock(label="Текст кнопки", required=False)
    page = blocks.PageChooserBlock(label="Страница сайта", required=False)
    url = blocks.URLBlock(label="или внешняя ссылка", required=False)

    class Meta:
        label = "Кнопка"
        icon = "link"


class HeroSlideBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Текст", required=False)
    image = ImageChooserBlock(label="Изображение", required=False)
    theme = blocks.ChoiceBlock(choices=[("yellow", "Жёлтый"), ("dark", "Чёрный"), ("light", "Светлый")],
                               default="yellow", label="Фон")
    link = LinkBlock(required=False)

    class Meta:
        label = "Слайд"
        icon = "image"


class SectionHeadingBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Подзаголовок", required=False)

    class Meta:
        label = "Заголовок раздела"
        icon = "title"
        template = "blocks/heading.html"


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(label="Изображение")
    caption = blocks.CharBlock(label="Подпись", required=False)
    wide = blocks.BooleanBlock(label="На всю ширину", required=False)

    class Meta:
        label = "Изображение"
        icon = "image"
        template = "blocks/image.html"


class StatItem(blocks.StructBlock):
    value = blocks.CharBlock(label="Число", help_text="Напр. 23 или 2014")
    label = blocks.CharBlock(label="Подпись")


ICON_CHOICES = [("check", "Галочка"), ("store", "Магазин"), ("tag", "Ценник"), ("clock", "Часы"), ("paw", "Лапка"),
                ("pin", "Метка"), ("work", "Портфель"), ("partner", "Рукопожатие"), ("phone", "Телефон")]


class AdvantageBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=ICON_CHOICES, default="check", label="Иконка")
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Текст", required=False)

    class Meta:
        label = "Преимущество"
        icon = "pick"


class StepBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Текст", required=False)

    class Meta:
        label = "Шаг"
        icon = "list-ol"


class AggregatorBlock(blocks.StructBlock):
    name = blocks.CharBlock(label="Название")
    logo = ImageChooserBlock(label="Логотип", required=False)
    url = blocks.URLBlock(label="Ссылка на Zoo Planeta в сервисе", required=False)
    note = blocks.CharBlock(label="Примечание", required=False, help_text="Напр. «Доставка от 30 минут»")

    class Meta:
        label = "Сервис доставки"
        icon = "link-external"


class StatsBlock(blocks.StructBlock):
    items = blocks.ListBlock(StatItem(), label="Показатели", min_num=2, max_num=6)

    class Meta:
        label = "Цифры"
        icon = "list-ol"
        template = "blocks/stats.html"


class TextImageBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.RichTextBlock(label="Текст", features=["bold", "italic", "link", "ul", "ol"])
    image = ImageChooserBlock(label="Изображение", required=False)
    image_left = blocks.BooleanBlock(label="Картинка слева", required=False)
    link = LinkBlock(required=False)

    class Meta:
        label = "Текст + изображение"
        icon = "doc-full"
        template = "blocks/text_image.html"


class CardItem(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Текст", required=False)
    image = ImageChooserBlock(label="Изображение", required=False)
    page = blocks.PageChooserBlock(label="Ссылка", required=False)


class CardsBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.TextBlock(label="Подзаголовок", required=False)
    columns = blocks.ChoiceBlock(choices=[("2", "2"), ("3", "3"), ("4", "4")], default="3", label="Колонок")
    style = blocks.ChoiceBlock(choices=[("plain", "Простые"), ("numbered", "С номерами"), ("photo", "Фото сверху")],
                               default="plain", label="Вид")
    items = blocks.ListBlock(CardItem(), label="Карточки")

    class Meta:
        label = "Карточки"
        icon = "grip"
        template = "blocks/cards.html"


class CategoryItem(blocks.StructBlock):
    title = blocks.CharBlock(label="Название")
    text = blocks.CharBlock(label="Что входит", required=False)
    image = ImageChooserBlock(label="Фото", required=False)


class CategoriesBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.TextBlock(label="Подзаголовок", required=False)
    items = blocks.ListBlock(CategoryItem(), label="Категории")

    class Meta:
        label = "Категории товаров"
        icon = "folder-open-inverse"
        template = "blocks/categories.html"


class TimelineItem(blocks.StructBlock):
    year = blocks.CharBlock(label="Год")
    title = blocks.CharBlock(label="Событие")
    text = blocks.TextBlock(label="Описание", required=False)


class TimelineBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    items = blocks.ListBlock(TimelineItem(), label="События")

    class Meta:
        label = "История (таймлайн)"
        icon = "date"
        template = "blocks/timeline.html"


class CTABlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок")
    text = blocks.TextBlock(label="Текст", required=False)
    link = LinkBlock()
    theme = blocks.ChoiceBlock(choices=[("yellow", "Жёлтый"), ("dark", "Чёрный")], default="yellow", label="Фон")

    class Meta:
        label = "Призыв к действию"
        icon = "pick"
        template = "blocks/cta.html"


class LogosBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    names = blocks.ListBlock(blocks.CharBlock(label="Название"), label="Названия (если нет логотипов)", required=False)
    logos = blocks.ListBlock(ImageChooserBlock(label="Логотип"), label="Логотипы", required=False)

    class Meta:
        label = "Бренды / партнёры"
        icon = "group"
        template = "blocks/logos.html"


class FAQItem(blocks.StructBlock):
    question = blocks.CharBlock(label="Вопрос")
    answer = blocks.RichTextBlock(label="Ответ", features=["bold", "italic", "link", "ul"])


class FAQBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    items = blocks.ListBlock(FAQItem(), label="Вопросы")

    class Meta:
        label = "Вопросы и ответы"
        icon = "help"
        template = "blocks/faq.html"


class GalleryBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    images = blocks.ListBlock(ImageChooserBlock(label="Фото"), label="Фотографии", min_num=1)

    class Meta:
        label = "Фотогалерея"
        icon = "image"
        template = "blocks/gallery.html"


class PersonItem(blocks.StructBlock):
    photo = ImageChooserBlock(label="Фото", required=False)
    name = blocks.CharBlock(label="Имя")
    role = blocks.CharBlock(label="Должность", required=False)
    quote = blocks.TextBlock(label="Фраза от первого лица", required=False,
                             help_text="Коротко: за что отвечает, напр. «Отвечаю за то, чтобы…»")


class TeamBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.TextBlock(label="Подзаголовок", required=False)
    people = blocks.ListBlock(PersonItem(), label="Люди")

    class Meta:
        label = "Команда"
        icon = "group"
        template = "blocks/team.html"


class StoryItem(blocks.StructBlock):
    photo = ImageChooserBlock(label="Фото", required=False)
    name = blocks.CharBlock(label="Имя")
    role = blocks.CharBlock(label="Должность", required=False)
    story = blocks.TextBlock(label="История", help_text="2–3 предложения от первого лица")


class StoriesBlock(blocks.StructBlock):
    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.TextBlock(label="Подзаголовок", required=False)
    items = blocks.ListBlock(StoryItem(), label="Истории", min_num=1, max_num=6)

    class Meta:
        label = "Истории сотрудников"
        icon = "openquote"
        template = "blocks/stories.html"


class StoresMapBlock(blocks.StructBlock):
    """Map of every store with the store count — filled automatically from the store pages."""

    title = blocks.CharBlock(label="Заголовок", required=False)
    text = blocks.TextBlock(label="Текст", required=False)

    class Meta:
        label = "Карта магазинов (автоматически)"
        icon = "site"
        template = "blocks/stores_map.html"

    def get_context(self, value, parent_context=None):
        from stores.models import StoreIndexPage
        ctx = super().get_context(value, parent_context)
        page = (parent_context or {}).get("page")
        locale = getattr(page, "locale", None)
        index = StoreIndexPage.objects.live().filter(locale=locale).first() if locale else None
        stores = list(index.stores()) if index else []
        ctx.update(store_index=index, map_stores=[s.public_dict() for s in stores], map_count=len(stores),
                   map_districts=len({s.district for s in stores if s.district}))
        return ctx


class RichTextSection(blocks.RichTextBlock):
    class Meta:
        label = "Текст"
        icon = "pilcrow"
        template = "blocks/richtext.html"


def body_blocks():
    return [
        ("heading", SectionHeadingBlock()),
        ("text", RichTextSection(features=["h2", "h3", "bold", "italic", "link", "ul", "ol", "hr"])),
        ("text_image", TextImageBlock()),
        ("image", ImageBlock()),
        ("stats", StatsBlock()),
        ("cards", CardsBlock()),
        ("categories", CategoriesBlock()),
        ("timeline", TimelineBlock()),
        ("gallery", GalleryBlock()),
        ("team", TeamBlock()),
        ("stories", StoriesBlock()),
        ("stores_map", StoresMapBlock()),
        ("logos", LogosBlock()),
        ("faq", FAQBlock()),
        ("cta", CTABlock()),
    ]
