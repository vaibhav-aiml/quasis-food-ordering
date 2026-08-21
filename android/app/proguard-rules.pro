# Proguard rules for Food Ordering Accessibility Service
-keepattributes *Annotation*
-keepclassmembers class * {
    @kotlinx.serialization.Serializable *;
}
