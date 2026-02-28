package com.happynews.app.utils

import java.time.LocalDate
import java.time.ZoneId

object DayKeyUtil {
    fun todayJst(): String = LocalDate.now(ZoneId.of("Asia/Tokyo")).toString()
}
