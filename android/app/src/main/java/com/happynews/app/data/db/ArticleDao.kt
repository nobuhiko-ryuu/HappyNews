package com.happynews.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ArticleDao {
    @Query("SELECT * FROM articles WHERE dayKey = :dayKey ORDER BY happyScore DESC, publishedAt DESC")
    fun getByDayKey(dayKey: String): Flow<List<ArticleEntity>>

    @Query("SELECT * FROM articles WHERE dayKey = :dayKey ORDER BY happyScore DESC, publishedAt DESC")
    suspend fun getByDayKeyOnce(dayKey: String): List<ArticleEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(articles: List<ArticleEntity>)

    @Query("UPDATE articles SET isBookmarked = :isBookmarked WHERE id = :id")
    suspend fun updateBookmark(id: String, isBookmarked: Boolean)

    @Query("SELECT * FROM articles WHERE isBookmarked = 1 ORDER BY cachedAt DESC")
    fun getBookmarks(): Flow<List<ArticleEntity>>

    @Query("SELECT * FROM articles WHERE id = :id LIMIT 1")
    suspend fun getById(id: String): ArticleEntity?

    @Query("DELETE FROM articles WHERE cachedAt < :cutoff AND isBookmarked = 0")
    suspend fun deleteOldCache(cutoff: Long)
}
