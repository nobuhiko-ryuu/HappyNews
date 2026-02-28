package com.happynews.app.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "articles")
data class ArticleEntity(
    @PrimaryKey val id: String,
    val title: String,
    val summary3lines: String,
    val sourceName: String,
    val sourceUrl: String,
    val originalUrl: String,
    val thumbnailUrl: String?,
    val publishedAt: String,
    val tags: String,           // JSON配列文字列
    val category: String,
    val happyScore: Float,
    val dayKey: String,
    val isBookmarked: Boolean = false,
    val cachedAt: Long = System.currentTimeMillis(),
)
