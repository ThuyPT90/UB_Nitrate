# -*- coding: utf-8 -*-

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_comments.forms import CommentDetailsForm

COMMENT_MAX_LENGTH = getattr(settings, "COMMENT_MAX_LENGTH", 10000)


class SimpleForm(CommentDetailsForm):
    name = forms.CharField(
        label=_("Name"),
        widget=forms.HiddenInput,
        max_length=50,
        required=False,
    )
    email = forms.EmailField(label=_("Email address"), widget=forms.HiddenInput, required=False)
    url = forms.URLField(label=_("URL"), widget=forms.HiddenInput, required=False)
    comment = forms.CharField(
        label=_("Comment"),
        widget=forms.Textarea,
        max_length=COMMENT_MAX_LENGTH,
    )

    def clean_timestamp(self):
        # return self.cleaned_data["timestamp"]

        import time

        return str(time.time()).split(".")[0]

    def get_form(self):
        # Use our custom comment model instead of the built-in one.
        return SimpleForm
