# dontbeevilmirror

The foremost source of Android apps is the Google Play Store. This is
not great, because the Google Play Store requires you to sign in to a
Google account on your Android phone, which of course allows Google to
[track your every movement](https://contrachrome.com/). There is no
technical reason that you should have to log in to a Google account to
download Android apps, given that the apps are free and everyone
receives the same version. The sole purpose is to allow Google to spy
on you and monetize your personal life.

To work around the problem, **dontbeevilmirror** is a simple
anonymizing proxy for Google Play. On the frontend, you navigate an
interface similar to Google Play to download and install apps. On the
backend, these requests are anonymized and filtered through a shared
Google account that I have registered for the project. Furthermore,
once an app is downloaded once, a copy is saved so that future
downloads don't go to Google.

## Local development

To compile the googlecurl binary:

* Install Go
* Go into `googlecurl` and run `go build`

To use the API library:

* Install Poetry
* Go into `gplayapi` and run `poetry install`
* Make sure compiled googlecurl is on the PATH
* Start a shell with `poetry run python`
* `from dontbeevilmirror.api import GooglePlay, InitialAuthInfo,
  AuthInfo, CheckinInfo, Credentials; g = GooglePlay()`
* For initial login, `g.perform_initial_login(email, password)` and
  then save the result of `g.get_credentials()`
* For restoring session, `g.set_credentials(creds)`
* API methods: `g.search(query)` (doesn't require auth),
  `g.get_details_single(app_id)`, `g.get_details_multiple(*app_ids)`,
  `g.get_download(app)`, `g.check_authentication()`

To use the command-line tool:

* Not finished yet

To run the webserver:

* Install Docker Compose
* Go into `server` and copy `.env.sample` to `.env`
* Fill in `GOOGLE_EMAIL` and `GOOGLE_PASSWORD`, generate a random
  string for `POSTGRES_PASSWORD`, pick fake values for `B2_BUCKET` and
  `B2_URL_BASE` (they don't matter if `B2_USE_MOCK=1`)
* To use real B2, set `B2_USE_MOCK=0`, fill in `B2_KEY_ID` and
  `B2_KEY_SECRET`, set `B2_BUCKET`, and set `B2_URL_BASE` to something
  like `https://example.com/file/` where `example.com` is a CNAME to
  your Backblaze CDN server
* Run `docker-compose up`

To compile the Android app:

* Install JDK 17 and make it available (`JAVA_HOME` etc)
* Install Android SDK 32 and make it available (`ANDROID_HOME` etc).
  One way is with sdkmanager
* Go into `app` and run `./gradlew build`
* Compiled app is in `./app/build/outputs/apk/debug/app-debug.apk`
* Install with `adb install`

## Credits

The reverse-engineered logic for accessing the Google Play API was
determined by inspection of the code of
[Raccoon](https://github.com/onyxbits/raccoon4), which is provided
under the terms of the [Apache
License](https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/LICENSE).

Adaption to Python was aided by inspection of the code of
[googleplay-api](https://github.com/marty0678/googleplay-api), which
is provided under the terms of the [BSD License and GNU Public
License](https://github.com/marty0678/googleplay-api/blob/master/LICENSE.md).
Note that no code is incorporated from this project, and copy-left
provisions do not apply since, under U.S. law, implementations are not
creative works and hence not copyrightable when they are the only
possible way to accomplish the task at hand (e.g. satisfying Google
authentication requirements).
