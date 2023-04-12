plugins {
    id("com.android.application") version "7.4.2"
}

repositories {
    google()
    mavenCentral()
}

android {
    compileSdkVersion(32)
    namespace = "codes.radian.dontbeevil"
    defaultConfig {
        applicationId = "codes.radian.dontbeevil"
        minSdkVersion(16)
        targetSdkVersion(32)
        versionCode = 1
        versionName = "0.1.0"
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
        }
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.2.0")
    implementation("com.google.android.material:material:1.2.0")
    implementation("androidx.constraintlayout:constraintlayout:2.0.4")
}
