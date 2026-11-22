"""Forms for the News app."""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, Article, Newsletter, Publisher


class RegisterForm(UserCreationForm):
    """Sign up form where the user picks their role.

    Publishers also give their publication's name and description.
    """
    email = forms.EmailField(required=True)
    publication_name = forms.CharField(
        max_length=100,
        required=False,
        help_text='Publishers only: the name of your publication.',
    )
    publication_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Publishers only (optional).',
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']

    def clean_email(self):
        """Stops two accounts using the same email."""
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('That email is already being used.')
        return email

    def clean(self):
        """Publishers must give a publication name that isn't taken."""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        name = cleaned_data.get('publication_name', '').strip()

        if role == CustomUser.PUBLISHER:
            if not name:
                self.add_error(
                    'publication_name',
                    'Publishers must give their publication a name.',
                )
            elif Publisher.objects.filter(name__iexact=name).exists():
                self.add_error(
                    'publication_name',
                    'A publication with that name already exists.',
                )
        cleaned_data['publication_name'] = name
        return cleaned_data

    def save(self, commit=True):
        """Saves the user, and makes the publication for publishers."""
        user = super().save(commit=commit)
        if commit and user.role == CustomUser.PUBLISHER:
            Publisher.objects.create(
                owner=user,
                name=self.cleaned_data['publication_name'],
                description=self.cleaned_data['publication_description'],
            )
        return user


class PublisherForm(forms.ModelForm):
    """Lets a publisher change their publication's details."""

    class Meta:
        model = Publisher
        fields = ['name', 'description']


class AddStaffForm(forms.Form):
    """Lets a publisher add an editor or journalist by their username."""
    username = forms.CharField(max_length=150)

    def clean_username(self):
        """The user must exist and be an editor or journalist."""
        username = self.cleaned_data['username'].strip()
        user = CustomUser.objects.filter(username__iexact=username).first()
        if user is None:
            raise forms.ValidationError('No user with that username.')
        if user.role not in [CustomUser.EDITOR, CustomUser.JOURNALIST]:
            raise forms.ValidationError(
                'You can only add editors and journalists.'
            )
        # pass the user on to the view
        self.staff_member = user
        return username


class ArticleForm(forms.ModelForm):
    """Form for writing or editing an article."""

    class Meta:
        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {'content': forms.Textarea(attrs={'rows': 10})}

    def __init__(self, *args, journalist=None, **kwargs):
        """Only shows the publishers the journalist works for."""
        super().__init__(*args, **kwargs)

        # an article can't move between publishers once it is published
        if self.instance.pk and self.instance.approved:
            del self.fields['publisher']
            return

        self.fields['publisher'].required = False
        self.fields['publisher'].empty_label = 'Independent (no publisher)'
        if journalist is not None:
            self.fields['publisher'].queryset = Publisher.objects.filter(
                journalists=journalist
            )


class NewsletterForm(forms.ModelForm):
    """Form for making or editing a newsletter."""

    class Meta:
        model = Newsletter
        fields = ['title', 'description', 'publisher', 'articles']
        widgets = {'articles': forms.CheckboxSelectMultiple}

    def __init__(self, *args, journalist=None, **kwargs):
        """Only approved articles and the journalist's publishers."""
        super().__init__(*args, **kwargs)
        self.fields['articles'].queryset = Article.objects.filter(
            approved=True
        )
        self.fields['publisher'].required = False
        self.fields['publisher'].empty_label = 'Independent (no publisher)'
        if journalist is not None:
            self.fields['publisher'].queryset = Publisher.objects.filter(
                journalists=journalist
            )
