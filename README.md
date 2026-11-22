# News Application

A news website made with Django, Django REST framework and MariaDB.

- **Publishers** run a publication and add their own editors and journalists
- **Journalists** write articles and newsletters
- **Editors** approve the articles from their publisher
- **Readers** read articles and subscribe to publishers and journalists

When an article is approved (or a journalist publishes an independent
article), a Django signal emails it to the subscribers and sends it to the
app's own API at `/api/approved/`.

## What you need

- Python 3.12 or newer (Django 6.1 needs it)
- MariaDB running on your computer
- Git

## How to run

1. Clone the project and go into its folder:
   ```
   git clone https://github.com/zaheermia/news-application.git
   cd news-application
   ```

2. Open the MariaDB shell (it asks for your MariaDB root password):
   ```
   mariadb -u root -p
   ```
   On a Mac with Homebrew, `sudo mariadb` also works.

3. In the MariaDB shell, make the database and a user, then leave:
   ```
   CREATE DATABASE news_db CHARACTER SET utf8mb4;
   CREATE USER 'news_user'@'localhost' IDENTIFIED BY 'your-password';
   GRANT ALL PRIVILEGES ON news_db.* TO 'news_user'@'localhost';
   EXIT;
   ```

4. Make a virtual environment and turn it on:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
   On Windows use `venv\Scripts\activate` instead.

5. Install the packages:
   ```
   pip install -r requirements.txt
   ```

6. Make a secret key and copy what it prints:
   ```
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

7. Make a `.env` file next to `manage.py` with the secret key and your
   database details:
   ```
   SECRET_KEY=paste-the-secret-key-here
   DB_NAME=news_db
   DB_USER=news_user
   DB_PASSWORD=your-password
   ```

8. Make the tables and start the server:
   ```
   python manage.py migrate
   python manage.py runserver
   ```

9. Go to http://127.0.0.1:8000/

## How the app works

Follow these steps in order to see every part of the app. Log out between
each account.

1. **Register a publisher.** On the Register page pick **Publisher** and type
   a publication name. This makes the publication and opens **My Publication**.
2. **Register an editor and a journalist.** Pick those roles on the Register page.
3. **The publisher adds their staff.** Log in as the publisher, open
   **My Publication** and add the editor and journalist by their username.
4. **Register a reader.** Open **Publishers**, pick the publication and click
   **Subscribe**. You can also subscribe to a journalist on their page.
5. **The journalist writes articles.** Click **Write Article**.
   - Pick the publication: the article waits for its editor.
   - Pick **Independent**: there is no editor, so the journalist clicks
     **Publish** on **My Articles** when they are happy with it.
6. **The editor approves.** Log in as the editor, open **Review Articles**
   and click **Approve**. Editors only see their own publishers' articles.
7. **Subscribers are told.** When an article is approved or published, the
   email to the subscribers and the `[APPROVED]` log from `/api/approved/`
   show up in the terminal (emails are printed, not really sent).
8. **The reader reads it.** Log in as the reader and open **My Feed**.
9. **Newsletters.** The journalist makes one with **New Newsletter** and sees
   theirs under **My Newsletters**. Editors can edit or delete the ones from
   their publishers. Everyone else can read them.

### What each role can see

| Role | Nav bar |
|---|---|
| Visitor | Home, Publishers, Newsletters, Login, Register |
| Reader | Home, Publishers, Newsletters, My Feed |
| Journalist | Home, My Articles, Write Article, My Newsletters, New Newsletter |
| Editor | Home, Review Articles, My Publishers, Newsletters |
| Publisher | Home, My Publication, Newsletters |

Journalists only see their publishers in the dropdown when writing.
Editors only see the publishers they work for.

## API

Get a token first, then send it with every request (I used Postman):

```
POST /api/token/   {"username": "...", "password": "..."}
Authorization: Token <your token>
```

| Method | URL | Who |
|---|---|---|
| GET | `/api/articles/` | all roles |
| POST | `/api/articles/` | journalists |
| GET | `/api/articles/subscribed/` | readers |
| GET / PUT / DELETE | `/api/articles/<id>/` | view: all, change: own journalist and its editors |
| POST | `/api/articles/<id>/approve/` | editors of the article's publisher |
| POST | `/api/articles/<id>/publish/` | the journalist, for their own independent article |
| POST | `/api/approved/` | editors and journalists (used by the signal) |
| GET / POST | `/api/newsletters/` | view: by role, create: journalists |
| GET / PUT / DELETE | `/api/newsletters/<id>/` | view: all, change: own journalist and its editors |
| GET | `/api/publishers/` | readers see all, staff see their own |

More detail is in `Planning/api.md`.

## Tests

The tests make their own test database, so the database user needs to be
allowed to make it.

1. Open the MariaDB shell again:
   ```
   mariadb -u root -p
   ```

2. Let `news_user` make the test database, then leave:
   ```
   GRANT ALL PRIVILEGES ON test_news_db.* TO 'news_user'@'localhost';
   EXIT;
   ```

3. Run the tests (with the virtual environment turned on):
   ```
   python manage.py test
   ```

The tests are in `news/tests.py`. They check every role, subscriptions,
publishing, newsletters, publisher staff and the approval signal (the email
and `/api/approved/` are mocked).

## Admin page

The admin page is only for maintenance. Everything the app needs can be
done on the website. If you want to use it:

```
python manage.py createsuperuser
```

Then go to http://127.0.0.1:8000/admin/

## Planning

The `Planning` folder has the requirements, page layout, API plan, security
notes, error handling, the class diagram and a sequence diagram for every use case.
