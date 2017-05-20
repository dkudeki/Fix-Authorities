SELECT DISTINCT /*csv*/ INDEX_TYPE.INDEX_NAME,
	AUTH_HEADING.AUTH_ID,
	HEADING.HEADING_ID,
	HEADING.DISPLAY_HEADING,
	AUTH_HEADING.DISPLAY_HEADING,
	HEADING.NORMAL_HEADING,
	HEADING.INDEX_TYPE,
	BIB_TEXT.BIB_ID,
	BIB_TEXT.NETWORK_NUMBER AS OCLCNum,
	BIB_TEXT.TITLE_BRIEF,
	AUTH_HEADING.HEADING_ID_POINTER,
	AUTH_HEADING.HEADING_ID_POINTEE,
	HEADING_TYPE.HEADING_TYPE_DESC,
	REFERENCE_TYPE.REFERENCE_TYPE_DESC,
	AUTH_HEADING.REFERENCE_TYPE
FROM (
		(
			(
				UIUDB.HEADING_TYPE
				INNER JOIN (
					(
						(
							(
								UIUDB.AUTH_HEADING 
								INNER JOIN UIUDB.HEADING 
								ON AUTH_HEADING.HEADING_ID_POINTER = HEADING.HEADING_ID
							)
							INNER JOIN (
								UIUDB.BIB_HEADING 
								INNER JOIN UIUDB.BIB_TEXT 
								ON BIB_HEADING.BIB_ID = BIB_TEXT.BIB_ID
							)
							ON HEADING.HEADING_ID = BIB_HEADING.HEADING_ID
						)
						INNER JOIN UIUDB.INDEX_TYPE
						ON HEADING.INDEX_TYPE = INDEX_TYPE.INDEX_TYPE
					)
					INNER JOIN UIUDB.REFERENCE_TYPE
					ON AUTH_HEADING.REFERENCE_TYPE = REFERENCE_TYPE.REFERENCE_TYPE
				)
				ON (HEADING_TYPE.HEADING_TYPE = HEADING.HEADING_TYPE)
				AND (HEADING_TYPE.INDEX_TYPE = HEADING.INDEX_TYPE)
			)
			INNER JOIN UIUDB.BIB_MASTER
			ON BIB_MASTER.BIB_ID = BIB_TEXT.BIB_ID
		)
		INNER JOIN UIUDB.BIB_ITEM
		ON BIB_ITEM.BIB_ID = BIB_MASTER.BIB_ID
	)
	INNER JOIN (
		(
			UIUDB.ITEM
			INNER JOIN UIUDB.LOCATION permloc
			ON ITEM.PERM_LOCATION = permloc.LOCATION_ID
		)
		LEFT JOIN UIUDB.LOCATION temploc
		ON ITEM.TEMP_LOCATION = temploc.LOCATION_ID
	)
	ON BIB_ITEM.ITEM_ID = ITEM.ITEM_ID
WHERE INDEX_TYPE.INDEX_NAME = 'Name'
	AND BIB_TEXT.BIB_ID BETWEEN '1000000' AND '1015001'
	AND AUTH_HEADING.REFERENCE_TYPE='s'
	AND substr(permloc.LOCATION_CODE,0,2) != 'rb'
	AND (temploc.LOCATION_CODE is null OR substr(temploc.LOCATION_CODE,0,2) != 'rb')
ORDER BY HEADING.NORMAL_HEADING;