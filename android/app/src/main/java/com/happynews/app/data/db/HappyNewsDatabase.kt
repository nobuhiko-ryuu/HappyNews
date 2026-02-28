package com.happynews.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [ArticleEntity::class], version = 1, exportSchema = false)
abstract class HappyNewsDatabase : RoomDatabase() {
    abstract fun articleDao(): ArticleDao
}
