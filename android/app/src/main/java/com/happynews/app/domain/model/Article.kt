package com.happynews.app.domain.model

data class Article(
    val id: String,
    val title: String,
    val summary3lines: String,
    val sourceName: String,
    val sourceUrl: String,
    val originalUrl: String,
    val thumbnailUrl: String?,
    val publishedAt: String,
    val tags: List<String>,
    val category: String,
    val happyScore: Float,
    val dayKey: String,
    val isBookmarked: Boolean = false,
)
