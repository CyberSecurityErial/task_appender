property agentTitle : "Notification Agent"

on run
	display notification "Notification Agent is ready to send task notifications." with title agentTitle
end run

on open openedItems
	if (count of openedItems) < 1 then
		error "Notification request folder is required." number 64
	end if

	set requestFolder to item 1 of openedItems
	set requestFolderPath to requestFolder as text
	set notificationTitle to my readRequiredText(requestFolderPath, "title.txt", "title")
	set notificationMessage to my readRequiredText(requestFolderPath, "message.txt", "message")
	set soundName to my readOptionalText(requestFolderPath, "sound.txt")

	if soundName is not "" then
		display notification notificationMessage with title notificationTitle sound name soundName
	else
		display notification notificationMessage with title notificationTitle
	end if
end open

on readRequiredText(folderPath, fileName, fieldName)
	set valueText to my readOptionalText(folderPath, fileName)
	if valueText is "" then
		error fieldName & " must not be empty." number 64
	end if
	return valueText
end readRequiredText

on readOptionalText(folderPath, fileName)
	set filePath to folderPath & fileName
	try
		set fileAlias to filePath as alias
	on error
		return ""
	end try

	set fileRef to open for access fileAlias
	try
		set valueText to read fileRef as «class utf8»
		close access fileRef
	on error errorMessage number errorNumber
		try
			close access fileRef
		end try
		error errorMessage number errorNumber
	end try
	return valueText
end readOptionalText
