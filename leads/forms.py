from django import forms

from core.ui import t
from leads.models import Feedback, JobApplication, PartnerRequest

RESUME_EXTENSIONS = (".pdf", ".doc", ".docx")
RESUME_MAX_BYTES = 5 * 1024 * 1024


class LeadForm(forms.ModelForm):
    """Common bits: translated labels, a honeypot field and the consent checkbox."""

    labels: dict[str, str] = {}
    company_url = forms.CharField(required=False, widget=forms.TextInput(
        attrs={"tabindex": "-1", "autocomplete": "off"}))  # honeypot: humans never see it
    consent = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, key in self.labels.items():
            if name in self.fields:
                self.fields[name].label = t(key)
        self.fields["consent"].label = t("f_consent")
        for field in self.fields.values():
            field.error_messages["required"] = t("f_required")

    def is_spam(self) -> bool:
        return bool(self.data.get("company_url"))


class JobApplicationForm(LeadForm):
    labels = {"name": "f_name", "phone": "f_phone", "email": "f_email", "message": "f_about_you",
              "resume": "f_resume"}

    class Meta:
        model = JobApplication
        fields = ["name", "phone", "email", "message", "resume"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "+998"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "message": forms.Textarea(attrs={"rows": 4}),
            "resume": forms.ClearableFileInput(attrs={"accept": ".pdf,.doc,.docx"}),
        }

    def clean_resume(self):
        f = self.cleaned_data.get("resume")
        if f and (not f.name.lower().endswith(RESUME_EXTENSIONS) or f.size > RESUME_MAX_BYTES):
            raise forms.ValidationError(t("f_bad_file"))
        return f


class PartnerRequestForm(LeadForm):
    labels = {"kind": "f_kind", "company": "f_company", "country": "f_country", "website": "f_website",
              "contact_name": "f_name", "email": "f_email", "phone": "f_phone", "category": "f_category",
              "message": "f_message"}

    class Meta:
        model = PartnerRequest
        fields = ["kind", "company", "country", "website", "contact_name", "email", "phone", "category", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "contact_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "company": forms.TextInput(attrs={"autocomplete": "organization"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [(k, t(f"kind_{k}")) for k in PartnerRequest.Kind.values]


class FeedbackForm(LeadForm):
    labels = {"topic": "f_topic", "name": "f_name", "phone": "f_phone", "email": "f_email", "store": "f_store",
              "message": "f_message"}

    class Meta:
        model = Feedback
        fields = ["topic", "name", "phone", "email", "store", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "+998"}),
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
        }

    def __init__(self, *args, stores=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].choices = [(k, t(f"topic_{k}")) for k in Feedback.Topic.values]
        if stores:
            self.fields["store"].widget = forms.Select(choices=[("", "—")] + [(s, s) for s in stores])

    def clean(self):
        data = super().clean()
        if not data.get("phone") and not data.get("email"):
            raise forms.ValidationError(t("f_phone_or_email"))
        return data
