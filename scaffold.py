import os

def w(path, content):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

w('settings.gradle.kts', '''pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "BillToStock"
include(":app")
''')

w('build.gradle.kts', '''plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
''')

w('app/build.gradle.kts', '''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.badal.billtostock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.badal.billtostock"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file("../keystore/badal-debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("release")
        }
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("org.apache.poi:poi-ooxml:5.2.5")
}
''')

w('app/src/main/AndroidManifest.xml', '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature android:name="android.hardware.camera" android:required="false" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.BillToStock">

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="com.badal.billtostock.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>

    </application>
</manifest>
''')

w('app/src/main/res/xml/file_paths.xml', '''<?xml version="1.0" encoding="utf-8"?>
<paths>
    <cache-path name="bill_photos" path="bills/" />
</paths>
''')

w('app/src/main/res/values/strings.xml', '''<resources>
    <string name="app_name">Bill To Stock</string>
</resources>
''')

w('app/src/main/res/values/colors.xml', '''<resources>
    <color name="brand_primary">#1B5E20</color>
    <color name="brand_accent">#FFB300</color>
</resources>
''')

w('app/src/main/res/values/themes.xml', '''<resources>
    <style name="Theme.BillToStock" parent="Theme.Material3.DayNight.NoActionBar">
        <item name="colorPrimary">@color/brand_primary</item>
        <item name="colorSecondary">@color/brand_accent</item>
    </style>
</resources>
''')

w('app/src/main/res/layout/activity_main.xml', '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <Button
        android:id="@+id/btnCapture"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Bill er chobi tolo" />

    <ImageView
        android:id="@+id/imgPreview"
        android:layout_width="match_parent"
        android:layout_height="220dp"
        android:layout_marginTop="12dp"
        android:scaleType="centerInside" />

    <ScrollView
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:layout_marginTop="12dp">

        <TextView
            android:id="@+id/txtResult"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textIsSelectable="true"
            android:text="OCR result ekhane dekhabe" />

    </ScrollView>

</LinearLayout>
''')

w('app/src/main/java/com/badal/billtostock/MainActivity.kt', '''package com.badal.billtostock

import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.badal.billtostock.databinding.ActivityMainBinding
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var photoUri: Uri? = null

    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success && photoUri != null) {
            runOcr(photoUri!!)
        }
    }

    private val cameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchCamera()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnCapture.setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                launchCamera()
            } else {
                cameraPermission.launch(android.Manifest.permission.CAMERA)
            }
        }
    }

    private fun launchCamera() {
        val dir = File(cacheDir, "bills")
        if (!dir.exists()) dir.mkdirs()
        val file = File(dir, "bill_${System.currentTimeMillis()}.jpg")
        photoUri = FileProvider.getUriForFile(this, "com.badal.billtostock.fileprovider", file)
        takePicture.launch(photoUri)
    }

    private fun runOcr(uri: Uri) {
        val bitmap = BitmapFactory.decodeStream(contentResolver.openInputStream(uri))
        binding.imgPreview.setImageBitmap(bitmap)
        val image = InputImage.fromBitmap(bitmap, 0)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        recognizer.process(image)
            .addOnSuccessListener { result ->
                binding.txtResult.text = result.text
            }
            .addOnFailureListener {
                Toast.makeText(this, "OCR fail holo: ${it.message}", Toast.LENGTH_LONG).show()
            }
    }
}
''')

w('.github/workflows/build.yml', '''name: Build APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 17
      - run: chmod +x gradlew
      - run: ./gradlew assembleDebug
      - uses: actions/upload-artifact@v4
        with:
          name: app-debug
          path: app/build/outputs/apk/debug/app-debug.apk
''')

w('.gitignore', '''*.iml
.gradle
/local.properties
/.idea
.DS_Store
/build
/captures
.externalNativeBuild
.cxx
''')

w('app/src/main/res/values/ic_launcher_background.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#1B5E20</color>
</resources>
''')

w('app/src/main/res/drawable/ic_launcher_foreground.xml', '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M34,28 L74,28 A6,6 0 0 1 80,34 L80,80 A6,6 0 0 1 74,86 L34,86 A6,6 0 0 1 28,80 L28,34 A6,6 0 0 1 34,28 Z"
        android:fillAlpha="0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M40,40 h28 v6 h-28 z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M40,52 h28 v6 h-28 z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M40,64 h20 v6 h-20 z" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M68,64 l10,10 l-4,4 l-10,-10 z" />
</vector>
''')

w('app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
''')

w('app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
''')

print('done')
