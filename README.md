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
