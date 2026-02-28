package com.happynews.app.ui.detail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.happynews.app.data.repository.ArticleRepository
import com.happynews.app.domain.model.Article
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class DetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: ArticleRepository,
) : ViewModel() {

    private val articleId: String = checkNotNull(savedStateHandle["articleId"])

    sealed class UiState {
        object Loading : UiState()
        data class Success(val article: Article) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            try {
                val article = repository.getArticle(articleId)
                _uiState.value = UiState.Success(article)
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "取得に失敗しました")
            }
        }
    }

    fun toggleBookmark() {
        val state = _uiState.value as? UiState.Success ?: return
        viewModelScope.launch {
            repository.toggleBookmark(state.article.id)
            _uiState.value = UiState.Success(
                state.article.copy(isBookmarked = !state.article.isBookmarked)
            )
        }
    }
}
