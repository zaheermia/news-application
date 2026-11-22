# API Plan

All requests send and get back JSON.

## Login
1. `POST /api/token/` with `username` and `password`
2. Send the token in every request: `Authorization: Token <token>`

## Endpoints

| Method | URL | Who | What it does |
|---|---|---|---|
| POST | /api/token/ | everyone | get a token |
| GET | /api/articles/ | all roles | all approved articles |
| POST | /api/articles/ | journalists | make an article |
| GET | /api/articles/subscribed/ | readers | articles from their subscriptions |
| GET | /api/articles/{id}/ | all roles | one article |
| PUT | /api/articles/{id}/ | its editors, own journalist | change an article |
| DELETE | /api/articles/{id}/ | its editors, own journalist | delete an article |
| POST | /api/articles/{id}/approve/ | editors of the article's publisher | approve it |
| POST | /api/articles/{id}/publish/ | the journalist | publish their own independent article |
| POST | /api/approved/ | editors and journalists (sent by the signal) | log an approved article |
| GET | /api/newsletters/ | all roles | readers: all, journalists: own, editors: their publishers' |
| POST | /api/newsletters/ | journalists | make a newsletter |
| GET | /api/newsletters/{id}/ | all roles | one newsletter |
| PUT | /api/newsletters/{id}/ | its editors, own journalist | change a newsletter |
| DELETE | /api/newsletters/{id}/ | its editors, own journalist | delete a newsletter |
| GET | /api/publishers/ | all roles | readers: all, staff: the ones they work for |

PUT only needs the fields you want to change.

## What the API sends back
- **Article** - id, title, content, author, publisher, publisher_name, created_at, approved
- **Newsletter** - id, title, description, created_at, author, publisher, publisher_name, articles (ids)
- **Publisher** - id, name, description, owner, editors, journalists
- **User** - id, username, role (no email or password)

## Example: make an article
```
POST /api/articles/
{"title": "New park", "content": "Text...", "publisher": 1}
```
Leave out `publisher` for an independent article. Then publish it with
`POST /api/articles/{id}/publish/` when it's ready.
