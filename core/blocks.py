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
        ("logos", LogosBlock()),
        ("faq", FAQBlock()),
        ("cta", CTABlock()),
    ]
