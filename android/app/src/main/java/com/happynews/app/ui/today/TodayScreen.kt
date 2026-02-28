package com.happynews.app.ui.today

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.happynews.app.R
import com.happynews.app.domain.model.Article
import com.happynews.app.ui.common.EmptyContent
import com.happynews.app.ui.common.ErrorContent
import com.happynews.app.ui.common.LoadingContent

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(
    viewModel: TodayViewModel = hiltViewModel(),
    onArticleClick: (String) -> Unit,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val pullState = rememberPullToRefreshState()

    Scaffold(topBar = {
        TopAppBar(title = { Text("ハッピーニュース") })
    }) { padding ->
        when (val state = uiState) {
            is TodayViewModel.UiState.Loading -> LoadingContent()
            is TodayViewModel.UiState.Error -> ErrorContent(
                message = state.message,
                onRetry = viewModel::loadArticles,
            )
            is TodayViewModel.UiState.Empty -> EmptyContent()
            is TodayViewModel.UiState.Success -> {
                PullToRefreshBox(
                    modifier = Modifier.padding(padding),
                    state = pullState,
                    isRefreshing = false,
                    onRefresh = viewModel::loadArticles,
                ) {
                    LazyColumn {
                        items(state.result.articles, key = { it.id }) { article ->
                            ArticleCard(
                                article = article,
                                onClick = { onArticleClick(article.id) },
                                onBookmarkToggle = { viewModel.toggleBookmark(article.id) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ArticleCard(
    article: Article,
    onClick: () -> Unit,
    onBookmarkToggle: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Row {
            AsyncImage(
                model = ImageRequest.Builder(LocalContext.current)
                    .data(article.thumbnailUrl)
                    .crossfade(true)
                    .build(),
                contentDescription = null,
                modifier = Modifier.size(80.dp),
                contentScale = ContentScale.Crop,
                error = painterResource(R.drawable.placeholder),
                placeholder = painterResource(R.drawable.placeholder),
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(8.dp),
            ) {
                Text(
                    article.title,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 2,
                )
                Text(
                    article.summary3lines,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 3,
                )
                Row {
                    Text(
                        article.sourceName,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = onBookmarkToggle) {
                        Icon(
                            imageVector = if (article.isBookmarked) Icons.Filled.Bookmark
                            else Icons.Outlined.BookmarkBorder,
                            contentDescription = "保存",
                        )
                    }
                }
            }
        }
    }
}
