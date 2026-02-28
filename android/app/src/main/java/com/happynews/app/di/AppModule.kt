package com.happynews.app.di

import android.content.Context
import androidx.room.Room
import com.google.firebase.auth.FirebaseAuth
import com.happynews.app.BuildConfig
import com.happynews.app.data.api.HappyNewsApi
import com.happynews.app.data.db.ArticleDao
import com.happynews.app.data.db.HappyNewsDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        })
        .addInterceptor { chain ->
            val uid = FirebaseAuth.getInstance().currentUser?.uid ?: ""
            chain.proceed(
                chain.request().newBuilder()
                    .addHeader("X-Uid", uid)
                    .build()
            )
        }
        .build()

    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    @Provides
    @Singleton
    fun provideHappyNewsApi(retrofit: Retrofit): HappyNewsApi =
        retrofit.create(HappyNewsApi::class.java)

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): HappyNewsDatabase =
        Room.databaseBuilder(context, HappyNewsDatabase::class.java, "happynews.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    @Singleton
    fun provideArticleDao(db: HappyNewsDatabase): ArticleDao = db.articleDao()
}
