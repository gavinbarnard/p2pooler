if (CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(XMRIG_64_BIT ON)
    add_definitions(-DXMRIG_64_BIT)
else()
    set(XMRIG_64_BIT OFF)
endif()

if (XMRIG_64_BIT AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64)$")
    add_definitions(-DRAPIDJSON_SSE2)
endif()

add_definitions(-DRAPIDJSON_WRITE_DEFAULT_FLAGS=6) # rapidjson::kWriteNanAndInfFlag | rapidjson::kWriteNanAndInfNullFlag
