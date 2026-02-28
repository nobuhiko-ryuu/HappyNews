package com.happynews.app.data.repository

import com.happynews.app.data.api.HappyNewsApi
import com.happynews.app.data.db.ArticleDao
import com.happynews.app.data.db.ArticleEntity
import com.happynews.app.domain.model.Article
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

data class ArticleListResult(val dayKey: String, val articles: List<Article>)

@Singleton
class ArticleRepository @Inject constructor(
    private val api: HappyNewsApi,
    private val dao: ArticleDao,
) {
    suspend fun getTodayArticles(): ArticleListResult {
        val latestDay = api.getLatestDay()
        val response = api.getArticlesByDay(latestDay.dayKey)
        val entities = response.articles.map { it.toEntity(latestDay.dayKey) }
        dao.insertAll(entities)
        return ArticleListResult(
            dayKey = response.dayKey,
            articles = response.articles.map { it.toDomain() }
        )
    }

    fun getCachedArticles(dayKey: String): Flow<List<Article>> =
        dao.getByDayKey(dayKey).map { list -> list.map { it.toDomain() } }

    suspend fun getArticle(id: String): Article {
        val cached = dao.getById(id)
        if (cached != null) return cached.toDomain()
        val response = api.getArticle(id)
        return Article(
            id = response.id,
            title = response.title,
            summary3lines = response.summary3lines,
            sourceName = response.sourceName,
            sourceUrl = response.sourceUrl,
            originalUrl = response.originalUrl,
            thumbnailUrl = response.thumbnailUrl,
            publishedAt = response.publishedAt,
            tags = response.tags,
            category = response.category,
            happyScore = response.happyScore,
            dayKey = response.dayKey,
        )
    }

    suspend fun toggleBookmark(id: String) {
        val entity = dao.getById(id) ?: return
        val newState = !entity.isBookmarked
        dao.updateBookmark(id, newState)
        try {
            if (newState) api.addBookmark(id) else api.removeBookmark(id)
        } catch (_: Exception) {
            // ネットワークエラー時はローカル状態を優先
        }
    }

    fun getBookmarks(): Flow<List<Article>> =
        dao.getBookmarks().map { list -> list.map { it.toDomain() } }
}

private fun com.happynews.app.data.api.model.ArticleDto.toEntity(dayKey: String) = ArticleEntity(
    id = id,
    title = title,
    summary3lines = summary3lines,
    sourceName = sourceName,
    sourceUrl = sourceUrl,
    originalUrl = originalUrl,
    thumbnailUrl = thumbnailUrl,
    publishedAt = publishedAt,
    tags = tags.joinToString(","),
    category = category,
    happyScore = happyScore,
    dayKey = this.dayKey.ifEmpty { dayKey },
)

private fun com.happynews.app.data.api.model.ArticleDto.toDomain() = Article(
    id = id,
    title = title,
    summary3lines = summary3lines,
    sourceName = sourceName,
    sourceUrl = sourceUrl,
    originalUrl = originalUrl,
    thumbnailUrl = thumbnailUrl,
    publishedAt = publishedAt,
    tags = tags,
    category = category,
    happyScore = happyScore,
    dayKey = dayKey,
)

private fun ArticleEntity.toDomain() = Article(
    id = id,
    title = title,
    summary3lines = summary3lines,
    sourceName = sourceName,
    sourceUrl = sourceUrl,
    originalUrl = originalUrl,
    thumbnailUrl = thumbnailUrl,
    publishedAt = publishedAt,
    tags = tags.split(",").filter { it.isNotEmpty() },
    category = category,
    happyScore = happyScore,
    dayKey = dayKey,
    isBookmarked = isBookmarked,
)
