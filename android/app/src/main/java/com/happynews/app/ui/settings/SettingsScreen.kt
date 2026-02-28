package com.happynews.app.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel = hiltViewModel(),
    onNotificationClick: () -> Unit,
    onLegalClick: () -> Unit,
) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    var newWord by remember { mutableStateOf("") }

    Scaffold(topBar = { TopAppBar(title = { Text("設定") }) }) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .verticalScroll(rememberScrollState()),
        ) {
            // 通知設定へのリンク
            ListItem(
                headlineContent = { Text("通知設定") },
                modifier = Modifier.clickable(onClick = onNotificationClick),
            )
            HorizontalDivider()

            // ミュートワード
            Text(
                "ミュートワード",
                style = MaterialTheme.typography.titleSmall,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
            settings.muteWords.forEach { word ->
                ListItem(
                    headlineContent = { Text(word) },
                    trailingContent = {
                        IconButton(onClick = { viewModel.removeMuteWord(word) }) {
                            Icon(Icons.Default.Close, contentDescription = "削除")
                        }
                    },
                )
            }
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp),
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = newWord,
                    onValueChange = { newWord = it },
                    label = { Text("ミュートワードを追加") },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                )
                IconButton(
                    onClick = {
                        viewModel.addMuteWord(newWord)
                        newWord = ""
                    },
                    enabled = newWord.isNotBlank(),
                ) {
                    Icon(Icons.Default.Add, contentDescription = "追加")
                }
            }

            HorizontalDivider()
            // 法務/情報
            ListItem(
                headlineContent = { Text("法務/情報") },
                modifier = Modifier.clickable(onClick = onLegalClick),
            )
        }
    }
}
