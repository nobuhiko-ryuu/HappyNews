package com.happynews.app.data.api

import com.happynews.app.data.api.model.ArticleDetailResponse
import com.happynews.app.data.api.model.ArticleListResponse
import com.happynews.app.data.api.model.BookmarkListResponse
import com.happynews.app.data.api.model.LatestDayResponse
import com.happynews.app.data.api.model.SettingsRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

interface HappyNewsApi {
    @GET("v1/days/latest")
    suspend fun getLatestDay(): LatestDayResponse

    @GET("v1/days/{dayKey}/articles")
    suspend fun getArticlesByDay(@Path("dayKey") dayKey: String): ArticleListResponse

    @GET("v1/articles/{id}")
    suspend fun getArticle(@Path("id") id: String): ArticleDetailResponse

    @GET("v1/users/me/bookmarks")
    suspend fun getBookmarks(): BookmarkListResponse

    @POST("v1/users/me/bookmarks/{articleId}")
    suspend fun addBookmark(@Path("articleId") articleId: String): Response<Unit>

    @DELETE("v1/users/me/bookmarks/{articleId}")
    suspend fun removeBookmark(@Path("articleId") articleId: String): Response<Unit>

    @PUT("v1/users/me/settings")
    suspend fun updateSettings(@Body settings: SettingsRequest): Response<Unit>
}
