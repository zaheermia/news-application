# Layout (front end plan)

Every page uses `base.html` with a nav bar at the top and messages under it.

## Nav bar
- Not logged in: Home | Publishers | Newsletters | Login | Register
- Reader: Home | Publishers | Newsletters | My Feed | Logout
- Journalist: Home | My Articles | Write Article | My Newsletters | New Newsletter | Logout
- Editor: Home | Review Articles | My Publishers | Newsletters | Logout
- Publisher: Home | My Publication | Newsletters | Logout

## Pages
- **Home** - cards of approved articles (title, author, publisher, date)
- **Article** - the full article, with Approve / Publish / Edit / Delete buttons if allowed
- **Publishers** - all publishers for readers, only their own for editors
- **Publisher page** - info, staff, Subscribe button, its articles
- **Journalist page** - Subscribe button, their articles and newsletters
- **My Feed** - a reader's subscribed articles
- **My Articles** - a journalist's articles, with a Publish button on independent drafts
- **Review Articles** - an editor's list of pending articles with an Approve button
- **My Publication** - a publisher's staff list, add/remove staff, publication details
- **Newsletters / My Newsletters** - list and detail pages
- **Forms** - one form page for articles and newsletters (publisher dropdown only shows the journalist's publishers)
- **Delete** - asks "Are you sure?" first
- **Register and Login** - publishers also type their publication name

## UX choices
- Cards so articles are easy to scan
- Pending articles are marked in orange ("Waiting for approval" or "Not published yet")
- Buttons and links only show for people who are allowed to use them
- Journalists don't get a Publishers page, only the dropdown when writing
