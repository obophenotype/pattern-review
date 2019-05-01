**Patter review tool**

This app allows a community of pattern reviewers to review and sign off on patterns in a systematic fashion. The assumption is that every community member that is named as a pattern contributor has *signed off* on this pattern. 

The app parses all patterns that exist in a target directory, creates an overview table and, based on the users orcid and the patterns contributor list, highlights which patterns are not yet reviewed. The app user can then click on a pattern that was not yet reviewed by them, review it and sign off on it. During sign-off, the app users orcid is added to the patterns contributor list, and the pattern is then committed back to GitHub.

In order to run the app, first download the example [env.list](url) file. You will need to add your user name and password into this file. **Only do this is you are working on your personal machine, and make sure that you never share this file, as it contains your github password in clear text!** Now you can run the app (from the terminal, being in the same directory as your env.list file) as follows:

```
docker run -p 8050:8050 --env-file ./env.list obolibrary/patternreview
``` 

Give the app a minute or two to load, then go to your browser, and navigate to:

```
http://localhost:8050/
```

After a few seconds (10-20), the pattern overview page should be loaded.