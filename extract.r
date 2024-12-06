# Load the cricketdata package
library(cricketdata)

# Fetch and save Ball-by-Ball data
tryCatch({
  bbb_data <- fetch_cricsheet("bbb")
  write.csv(bbb_data, "d:/dbms_project/bbb_data.csv", row.names = FALSE)
  message("Ball-by-Ball data saved successfully.")
}, error = function(e) {
  message("Error fetching or saving Ball-by-Ball data: ", e$message)
})

# Fetch and save Match data
tryCatch({
  match_data <- fetch_cricsheet("match")
  write.csv(match_data, "d:/dbms_project/match_data.csv", row.names = FALSE)
  message("Match data saved successfully.")
}, error = function(e) {
  message("Error fetching or saving Match data: ", e$message)
})

# Fetch and save Player data
tryCatch({
  player_data <- fetch_cricsheet("player")
  write.csv(player_data, "d:/dbms_project/player_data.csv", row.names = FALSE)
  message("Player data saved successfully.")
}, error = function(e) {
  message("Error fetching or saving Player data: ", e$message)
})
