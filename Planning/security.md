# Security

## Website
- Passwords are hashed by Django and checked with Django's password rules
- Users go in a Reader, Editor, Journalist or Publisher group based on their role
- `@login_required` and `has_perm()` lock the pages
- Journalists can only change their own articles and newsletters
- Editors can only approve, change and delete articles from their own publishers
- Only the journalist can publish their own independent article
- Only a publisher account can add or remove its own staff
- Journalists can't open the publisher pages, editors only see their own publishers
- Approve, subscribe and delete only work with POST
- `{% csrf_token %}` in all forms
- Passwords and the secret key are in the `.env` file

## API
- Token login for every request (no token = 401)
- Only journalists can POST articles and newsletters
- Only editors of the article's publisher can approve
- Only the author can publish an independent article
- Readers can only view
- `approved` can't be set by sending it, only by the approve endpoint
- Journalists can only post for publishers they work for
- A published article can't be moved to another publisher
- The user serializer never sends emails or passwords
