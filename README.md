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
