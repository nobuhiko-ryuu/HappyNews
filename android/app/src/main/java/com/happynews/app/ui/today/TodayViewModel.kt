package com.happynews.app.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.happynews.app.data.repository.ArticleListResult
import com.happynews.app.data.repository.ArticleRepository
import com.happynews.app.domain.model.Article
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val repository: ArticleRepository,
) : ViewModel() {

    sealed class UiState {
        object Loading : UiState()
        data class Success(val result: ArticleListResult) : UiState()
        data class Error(val message: String) : UiState()
        object Empty : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        loadArticles()
    }

    fun loadArticles() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                val result = repository.getTodayArticles()
                _uiState.value = if (result.articles.isEmpty()) UiState.Empty
                else UiState.Success(result)
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "取得に失敗しました")
            }
        }
    }

    fun toggleBookmark(articleId: String) {
        viewModelScope.launch { repository.toggleBookmark(articleId) }
    }
}
