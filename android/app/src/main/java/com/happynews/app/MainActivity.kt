package com.happynews.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.happynews.app.ui.navigation.HappyNewsNavHost
import com.happynews.app.ui.navigation.Screen
import com.happynews.app.ui.theme.HappyNewsTheme
import dagger.hilt.android.AndroidEntryPoint

data class BottomNavItem(val route: String, val icon: ImageVector, val label: String)

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val _deepLinkRoute = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleDeepLink(intent)
        enableEdgeToEdge()
        setContent {
            HappyNewsTheme {
                MainScreen(
                    initialDeepLink = _deepLinkRoute.value,
                    onDeepLinkConsumed = { _deepLinkRoute.value = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleDeepLink(intent)
    }

    private fun handleDeepLink(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme == "happynews" && uri.host == "today") {
            _deepLinkRoute.value = Screen.Today.route
        }
    }
}

@Composable
fun MainScreen(
    initialDeepLink: String? = null,
    onDeepLinkConsumed: () -> Unit = {},
) {
    val navController = rememberNavController()
    val entry by navController.currentBackStackEntryAsState()
    val currentRoute = entry?.destination?.route

    val tabs = listOf(
        BottomNavItem(Screen.Today.route, Icons.Default.Home, "ホーム"),
        BottomNavItem(Screen.Bookmarks.route, Icons.Default.Bookmark, "保存"),
        BottomNavItem(Screen.Settings.route, Icons.Default.Settings, "設定"),
    )

    LaunchedEffect(initialDeepLink) {
        initialDeepLink?.let { route ->
            navController.navigate(route) {
                popUpTo(navController.graph.findStartDestination().id) { inclusive = false }
                launchSingleTop = true
            }
            onDeepLinkConsumed()
        }
    }

    Scaffold(bottomBar = {
        if (currentRoute in tabs.map { it.route }) {
            NavigationBar {
                tabs.forEach { item ->
                    NavigationBarItem(
                        icon = { Icon(item.icon, item.label) },
                        label = { Text(item.label) },
                        selected = currentRoute == item.route,
                        onClick = {
                            navController.navigate(item.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                    )
                }
            }
        }
    }) { _ ->
        HappyNewsNavHost(navController = navController)
    }
}
