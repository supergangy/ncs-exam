import java.io.FileInputStream
import java.util.Properties

// ── 배포 서명 ──────────────────────────────────────────────────────
//  `android/key.properties` 가 있으면 그 키로, 없으면 **디버그 키**로 짓는다.
//
//  디버그 키로 나간 APK 는 **갱신 경로가 위태롭다.** 그 키는 기기마다 자동
//  생성되는 것이라 파일이 사라지거나 기계가 바뀌면 같은 서명을 다시 만들 수 없다.
//  그러면 사용자는 지우고 다시 깔아야 하고, 그때 SharedPreferences 에 있던
//  **푼 기록이 함께 사라진다.** v1.1.0~v1.10.0 이 그 상태로 나갔다.
//
//  릴리스 키는 **만드는 사람이 암호를 정한다.** 한 번만 하면 된다 —
//
//    keytool -genkeypair -v -keystore ncspass-release.jks -keyalg RSA //            -keysize 2048 -validity 10000 -alias ncspass
//
//    android/key.properties 에
//      storeFile=<.jks 경로>
//      storePassword=<정한 암호>
//      keyAlias=ncspass
//      keyPassword=<정한 암호>
//
//  key.properties 와 .jks 는 커밋하지 않는다 (android/.gitignore 에 이미 있다).
//  **그 파일을 잃으면 갱신을 못 한다.** 따로 백업해 둔다.
val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) load(FileInputStream(keystorePropertiesFile))
}

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.supergangy.ncs_bank"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications 가 요구한다. 없으면 릴리즈 빌드가
        // `checkReleaseAarMetadata` 에서 멎는다 —
        //   Dependency ':flutter_local_notifications' requires core library desugaring
        //
        // 오래된 안드로이드에서도 최신 java.time 을 쓸 수 있게 바이트코드를 낮춰
        // 다시 쓰는 것이다. 알림이 시각을 다루므로 그 라이브러리를 탄다.
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        applicationId = "com.supergangy.ncs_bank"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            create("release") {
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // key.properties 가 생기는 순간 저절로 릴리스 키로 넘어간다.
            // 없는 동안은 디버그 키다 — 위 머리말의 경고를 보라.
            signingConfig = if (keystorePropertiesFile.exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

dependencies {
    // 위 isCoreLibraryDesugaringEnabled 를 켜면 이 라이브러리를 함께 넣어야 한다.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")
}

flutter {
    source = "../.."
}
