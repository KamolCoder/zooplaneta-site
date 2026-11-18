"""Requests sent from the site: job applications, partnership requests, customer feedback."""
from django.db import models

from leads.storage import private_storage


class Status(models.TextChoices):
    NEW = "new", "Новая"
    IN_WORK = "in_work", "В работе"
    DONE = "done", "Закрыта"
    SPAM = "spam", "Спам"


class LeadBase(models.Model):
    created_at = models.DateTimeField("Получена", auto_now_add=True, db_index=True)
    language = models.CharField("Язык", max_length=5, blank=True)
    page_url = models.CharField("Страница", max_length=500, blank=True)
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)
    manager_note = models.TextField("Заметка менеджера", blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class JobApplication(LeadBase):
    vacancy = models.ForeignKey("pages.VacancyPage", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="applications", verbose_name="Вакансия")
    vacancy_title = models.CharField("Вакансия (на момент отклика)", max_length=255, blank=True)
    name = models.CharField("Имя", max_length=150)
    phone = models.CharField("Телефон", max_length=32)
    email = models.EmailField("E-mail", blank=True)
    message = models.TextField("О себе", blank=True)
    resume = models.FileField("Резюме", upload_to="resumes/%Y/%m/", storage=private_storage, blank=True)

    class Meta(LeadBase.Meta):
        verbose_name = "Отклик на вакансию"
        verbose_name_plural = "Отклики на вакансии"

    def __str__(self):
        return f"{self.name} — {self.vacancy_title or 'резюме'}"


class PartnerRequest(LeadBase):
    class Kind(models.TextChoices):
        SUPPLIER = "supplier", "Поставка товаров"
        BRAND = "brand", "Производитель / дистрибуция"
        PREMISES = "premises", "Помещение"
        MARKETING = "marketing", "Реклама и маркетинг"
        OTHER = "other", "Другое"

    kind = models.CharField("Тип", max_length=16, choices=Kind.choices, default=Kind.SUPPLIER)
    company = models.CharField("Компания", max_length=200)
    country = models.CharField("Страна", max_length=100, blank=True)
    website = models.CharField("Сайт", max_length=200, blank=True)
    contact_name = models.CharField("Контактное лицо", max_length=150)
    email = models.EmailField("E-mail")
    phone = models.CharField("Телефон", max_length=32, blank=True)
    category = models.CharField("Категория / площадь", max_length=255, blank=True)
    message = models.TextField("Сообщение", blank=True)

    class Meta(LeadBase.Meta):
        verbose_name = "Заявка партнёра"
        verbose_name_plural = "Заявки партнёров"

    def __str__(self):
        return f"{self.company} ({self.get_kind_display()})"


class Feedback(LeadBase):
    class Topic(models.TextChoices):
        FEEDBACK = "feedback", "Отзыв или предложение"
        COMPLAINT = "complaint", "Жалоба"
        PRODUCT = "product", "Вопрос о товаре"
        OTHER = "other", "Другое"

    topic = models.CharField("Тема", max_length=16, choices=Topic.choices, default=Topic.FEEDBACK)
    name = models.CharField("Имя", max_length=150)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    email = models.EmailField("E-mail", blank=True)
    store = models.CharField("Магазин", max_length=200, blank=True)
    message = models.TextField("Сообщение")

    class Meta(LeadBase.Meta):
        verbose_name = "Обращение покупателя"
        verbose_name_plural = "Обращения покупателей"

    def __str__(self):
        return f"{self.name}: {self.get_topic_display()}"
