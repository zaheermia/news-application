# Requirements

## Users
- **Publisher** - runs a publication and adds its editors and journalists
- **Journalist** - writes articles and newsletters
- **Editor** - checks and approves articles for their publishers
- **Reader** - reads articles and newsletters, subscribes to publishers and journalists
- **Admin** - only for maintenance on the admin page

## Functional requirements

### Everyone
- Register (pick a role) and log in / log out
- See approved articles, journalists and newsletters

### Publishers can
- Make their publication when they register (name and description)
- Add editors and journalists to it by username, and remove them
- Change the publication's name and description

### Readers can
- See all publishers
- Subscribe and unsubscribe to publishers and journalists
- See a feed of articles from their subscriptions
- Get an email when a followed publisher or journalist has a new article

### Journalists can
- Write articles, either independent or for a publisher they work for
- Publish their own independent articles (they have no editor)
- Edit and delete their own articles
- Make, edit and delete their own newsletters (see them under My Newsletters)
- Only see their publishers in the article and newsletter dropdowns

### Editors can
- See the articles waiting for approval from the publishers they work for
- Approve those articles
- Edit and delete articles and newsletters from their publishers
- Only see the publishers they work for

### When an article is approved or published
- A `post_save` signal emails it to the subscribers
- The signal sends a POST to `/api/approved/` with the `requests` module

### API
- Token login at `/api/token/`
- Get, create, update and delete articles depending on role
- Approve (editors) and publish (journalists, independent only)
- Readers get only their subscribed articles at `/api/articles/subscribed/`
- Newsletters and publishers can be read through the API too

## Non-functional requirements
- **Security** - passwords hashed, pages locked by role, secret key and passwords in `.env`
- **Usability** - simple nav bar that changes for each role, clear messages
- **Reliability** - if the email or `/api/approved/` fails, the approval still saves
- **Maintainability** - PEP 8, docstrings, helper functions in `news/functions/`
- **Testing** - automated unit tests for the API
- **Database** - MariaDB

## Models (normalised)
- **CustomUser** - username, email, password, role, subscribed publishers, subscribed journalists
- **Publisher** - name, description, owner, editors, journalists
- **Article** - title, content, author, publisher, created at, approved
- **Newsletter** - title, description, created at, author, publisher, articles

How the tables are normalised:
- Each table has one id and only stores facts about itself
- Many-to-many links (subscriptions, publisher staff, newsletter articles) get their own link tables, so there are no lists inside one column
- The author, owner and publisher are stored as foreign keys, not copied names, so nothing is repeated
- An article or newsletter with no publisher is independent

## Groups and permissions

| Group | Articles | Newsletters | Publishers |
|---|---|---|---|
| Reader | view | view | view |
| Editor | view, change, delete, approve | view, change, delete | view |
| Journalist | add, view, change, delete | add, view, change, delete | view |
| Publisher | view | view | view, change |

- A user is put in the group for their role when they are saved
- If a user is not a reader, their subscriptions are emptied (the "None" value)
- A journalist's articles and newsletters are reverse relations (`user.articles`, `user.newsletters`)

## Diagrams
See the `Diagrams` folder: a class diagram and a sequence diagram for every use case.
