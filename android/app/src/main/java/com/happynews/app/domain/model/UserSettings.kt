package com.happynews.app.domain.model

data class UserSettings(
    val notificationEnabled: Boolean = false,
    val notificationHour: Int = 8,
    val muteWords: List<String> = emptyList(),
)
