try:
    from django.utils.timezone import now
except ImportError:
    from datetime.datetime import now  # noqa

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from podcasting.utils.twitter import can_tweet
from podcasting.utils.widgets import CustomAdminThumbnailWidget
from podcasting.models import Enclosure, Episode, Show


class BaseShowForm(forms.ModelForm):

    original_image = forms.ImageField(
        widget=CustomAdminThumbnailWidget,
        help_text=Show._meta.get_field("original_image").help_text)

    publish = forms.BooleanField(
        required=False,
        help_text=_("Checking this will publish this show on the site, no turning back."),
    )

    class Meta:
        model = Show
        fields = [
            "original_image",
            "author_text",
            "owner",
            "editor_email",
            "webmaster_email",
            "title", "subtitle", "description",
            "twitter_tweet_prefix",
            "feedburner", "itunes",
            "keywords", "organization", "license",
            "explicit", "link",
            "on_itunes",
            "publish",
        ]
        if "taggit" in settings.INSTALLED_APPS:
            fields.append("tags")


class ShowAddForm(BaseShowForm):

    def clean_publish(self):
        if self.cleaned_data["publish"]:
            self.instance.published = now()


class ShowChangeForm(BaseShowForm):

    def __init__(self, *args, **kwargs):
        super(ShowChangeForm, self).__init__(*args, **kwargs)
        self.fields["publish"].initial = bool(self.instance.published)

    def clean_publish(self):
        # clean_publish is called twice, skip the first time when instance is unset
        if not self.instance.pk:
            return
        # do nothing if already published
        if self.instance.published:
            return
        if self.cleaned_data["publish"]:
            self.instance.published = now()


class BaseEpisodeForm(forms.ModelForm):

    original_image = forms.ImageField(
        widget=CustomAdminThumbnailWidget,
        help_text=Episode._meta.get_field("original_image").help_text)

    publish = forms.BooleanField(
        required=False,
        help_text=_("Checking this will publish this episode on the site, no turning back."),
    )

    if can_tweet():
        tweet = forms.BooleanField(
            required=False,
            help_text=_("Checking this will send out a tweet announcing the episode."))

    class Meta:
        model = Episode
        fields = [
            "original_image",
            "author_text",
            "title", "subtitle",
            "description",
            "tracklist",
            "hours", "minutes", "seconds",
            "publish",
        ]
        if "taggit" in settings.INSTALLED_APPS:
            fields.append("tags")
        extra_fields_itunes = [
            "keywords",
            "explicit",
            "block",
        ]
        required_fields_itunes = [
            "author_text",
            "subtitle",
            "description",
            "original_image",
            "tags",
            "keywords",
            "explicit",
        ]

    def save(self):
        instance = super(BaseEpisodeForm, self).save()

        if can_tweet() and self.cleaned_data["tweet"]:
            instance.tweet()

        return instance

    def validate_published(self):
        if not self.instance.enclosure_set.all():
            raise forms.ValidationError(
                _("An episode must have at least one enclosure before publishing.\n "
                  "Uncheck, save this episode, and add an encoslure before publishing."))
        elif not self.instance.show.published:
            raise forms.ValidationError(_("The show for this episode is not yet published"))
        self.instance.published = now()


class EpisodeChangeForm(BaseEpisodeForm):

    def __init__(self, *args, **kwargs):
        super(EpisodeChangeForm, self).__init__(*args, **kwargs)
        self.fields["publish"].initial = bool(self.instance.published)

    def clean_publish(self):
        # clean_publish is called twice, skip the first time when instance is unset
        if not self.instance.pk:
            return
        # do nothing if already published
        if self.instance.published:
            return
        if self.cleaned_data["publish"]:
            self.validate_published()


class EpisodeITunesChangeForm(EpisodeChangeForm):
    def __init__(self, *args, **kwargs):
        super(EpisodeITunesChangeForm, self).__init__(*args, **kwargs)
        for key in self.Meta.required_fields_itunes:
            self.fields[key].required = True

    class Meta(EpisodeChangeForm.Meta):
        fields = EpisodeChangeForm.Meta.fields + EpisodeChangeForm.Meta.extra_fields_itunes


class EpisodeAddForm(BaseEpisodeForm):

    def clean_publish(self):
        if self.cleaned_data["publish"]:
            self.validate_published()


class EpisodeITunesAddForm(EpisodeAddForm):
    def __init__(self, *args, **kwargs):
        super(EpisodeITunesAddForm, self).__init__(*args, **kwargs)
        for key in self.Meta.required_fields_itunes:
            self.fields[key].required = True

    class Meta(EpisodeAddForm.Meta):
        fields = EpisodeAddForm.Meta.fields + EpisodeAddForm.Meta.extra_fields_itunes


class EnclosureForm(forms.ModelForm):

    class Meta:
        model = Enclosure
        fields = [
            "url",
            "mime",
            "size",
            "bitrate",
            "sample",
            "channel",
        ]

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove("episode")  # allow checking against the missing attribute

        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as err:
            self._update_errors(err.message_dict)


class AdminShowForm(forms.ModelForm):

    publish = forms.BooleanField(
        required=False,
        help_text=_("Checking this will publish this show on the site, no turning back."),
    )

    class Meta:
        model = Show

    def __init__(self, *args, **kwargs):
        super(AdminShowForm, self).__init__(*args, **kwargs)
        self.fields["publish"].initial = bool(self.instance.published)

    def clean_publish(self):
        # clean_publish is called twice, skip the first time when instance is unset
        if not self.instance.pk:
            return
        # do nothing if already published
        if self.instance.published:
            return
        if self.cleaned_data["publish"]:
            self.instance.published = now()


class AdminEpisodeForm(forms.ModelForm):

    publish = forms.BooleanField(
        required=False,
        help_text=_("Checking this will publish this episode on the site, no turning back."))

    if can_tweet():
        tweet = forms.BooleanField(
            required=False,
            help_text=_("Checking this will send out a tweet announcing the episode."))

    class Meta:
        model = Episode

    def __init__(self, *args, **kwargs):
        super(AdminEpisodeForm, self).__init__(*args, **kwargs)
        self.fields["publish"].initial = bool(self.instance.published)

    def validate_published(self):
        if not self.instance.enclosure_set.all():
            raise forms.ValidationError(
                _("An episode must have at least one enclosure before publishing.\n "
                  "Uncheck, save this episode, and add an encoslure before publishing."))
        elif not self.instance.show.published:
            raise forms.ValidationError(_("The show for this episode is not yet published"))
        self.instance.published = now()

    def clean_publish(self):
        # clean_publish is called twice, skip the first time when instance is unset
        if not self.instance.pk:
            return
        # do nothing if already published
        if self.instance.published:
            return
        if self.cleaned_data["publish"]:
            self.validate_published()

    def save(self):
        episode = super(AdminEpisodeForm, self).save(commit=False)

        episode.save()

        if can_tweet() and self.cleaned_data["tweet"]:
            episode.tweet()

        return episode
