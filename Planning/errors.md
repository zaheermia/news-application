# What Could Go Wrong

## Website
- **Wrong login** - show "Invalid username or password"
- **Username or email taken** - show an error on the register form
- **Publisher with no or a taken publication name** - show an error on the register form
- **Adding staff who doesn't exist or isn't an editor/journalist** - show an error on My Publication
- **No permission** - 403 "You are not allowed to do that"
- **Page or article doesn't exist** - 404 page
- **Article not approved yet** - only the author and its editors can see it

## API
- **No token or wrong token** - 401
- **Not allowed for your role** - 403
- **Missing or wrong data** - 400
- **Article already approved or published** - 400
- **Article doesn't exist** - 404

## Approval
- **Email fails** - error is printed, the approval still saves
- **`/api/approved/` is down** - error is caught and printed, the approval still saves
