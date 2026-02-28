package com.happynews.app.data.api.model

import com.google.gson.annotations.SerializedName

data class LatestDayResponse(
    @SerializedName("day_key") val dayKey: String,
)

data class ArticleListResponse(
    @SerializedName("day_key") val dayKey: String,
    val articles: List<ArticleDto>,
)

data class ArticleDetailResponse(
    val id: String,
    val title: String,
    @SerializedName("summary_3lines") val summary3lines: String,
    @SerializedName("source_name") val sourceName: String,
    @SerializedName("source_url") val sourceUrl: String,
    @SerializedName("original_url") val originalUrl: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("published_at") val publishedAt: String,
    val tags: List<String> = emptyList(),
    val category: String = "",
    @SerializedName("happy_score") val happyScore: Float = 0f,
    @SerializedName("day_key") val dayKey: String = "",
)

data class ArticleDto(
    val id: String,
    val title: String,
    @SerializedName("summary_3lines") val summary3lines: String,
    @SerializedName("source_name") val sourceName: String,
    @SerializedName("source_url") val sourceUrl: String,
    @SerializedName("original_url") val originalUrl: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("published_at") val publishedAt: String,
    val tags: List<String> = emptyList(),
    val category: String = "",
    @SerializedName("happy_score") val happyScore: Float = 0f,
    @SerializedName("day_key") val dayKey: String = "",
)

data class BookmarkListResponse(val bookmarks: List<ArticleDto>)

data class SettingsRequest(
    @SerializedName("notification_enabled") val notificationEnabled: Boolean? = null,
    @SerializedName("notification_time") val notificationTime: Int? = null,
    @SerializedName("mute_words") val muteWords: List<String>? = null,
    @SerializedName("fcm_token") val fcmToken: String? = null,
)
