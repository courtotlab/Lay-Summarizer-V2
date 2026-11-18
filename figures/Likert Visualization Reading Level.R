# ------------------------------------------------------------------------------
# Reading Grade Level Likert Chart (7 Ordered Levels)
# ------------------------------------------------------------------------------
library(tidyverse)
library(scales)
library(here)

# 1. Read raw CSV survey file
df_raw <- read_csv(here("data","Survey_Data_IntegratedSheet.csv"))

# 2. Reshape & transform data
df_long <- df_raw %>%
  pivot_longer(
    cols = matches("reading grade level", ignore.case = TRUE),
    names_to = "Question_Header",
    values_to = "Raw_Response"
  ) %>%
  drop_na(Raw_Response) %>%
  mutate(
    # Extract summary number (1 through 10)
    Summary_Num = as.numeric(str_extract(Question_Header, "\\d+")),
    
    # Map summary number to Source category
    Source = if_else(Summary_Num <= 5, "Full Text", "Abstract"),
    
    # Pattern matching for clean categorical labels
    Clean_Response = case_when(
      str_detect(Raw_Response, "Grades 1 to 2|Grades 1-2")   ~ "Grades 1 to 2",
      str_detect(Raw_Response, "Grades 3 to 4")             ~ "Grades 3 to 4",
      str_detect(Raw_Response, "Grades 5 to 6")             ~ "Grades 5 to 6",
      str_detect(Raw_Response, "Grades 7 to 8")             ~ "Grades 7 to 8",
      str_detect(Raw_Response, "Grades 9 to 10")            ~ "Grades 9 to 10",
      str_detect(Raw_Response, "Grades 11 to 12")           ~ "Grades 11 to 12",
      str_detect(Raw_Response, "Grade 12\\+ / University")  ~ "Grade 12+ / University",
      TRUE ~ NA_character_
    ),
    
    # Define ordered factor with all 7 levels
    Grade_Level = factor(
      Clean_Response,
      levels = c(
        "Grades 1 to 2",
        "Grades 3 to 4",
        "Grades 5 to 6",
        "Grades 7 to 8",
        "Grades 9 to 10",
        "Grades 11 to 12",
        "Grade 12+ / University"
      ),
      ordered = TRUE
    )
  )

# 3. Aggregate counts and derive group percentages
df_summary <- df_long %>%
  count(Source, Grade_Level, .drop = FALSE) %>%  # Retain 0-count levels
  group_by(Source) %>%
  mutate(Percentage = n / sum(n)) %>%
  ungroup()

# Reorder Source factor so "Full Text" renders on top horizontally
df_summary$Source <- factor(df_summary$Source, levels = c("Full Text", "Abstract"))

# Print summary table to RStudio console
print(df_summary)

# 4. Color palette definition (7-level gradient from green to red)
grade_colors <- c(
  "Grades 1 to 2"          = "#006837", # Dark Green
  "Grades 3 to 4"          = "#1a9641", # Green
  "Grades 5 to 6"          = "#a6d96a", # Light Green
  "Grades 7 to 8"          = "#ffffbf", # Soft Yellow
  "Grades 9 to 10"         = "#fdae61", # Orange
  "Grades 11 to 12"        = "#f46d43", # Dark Orange
  "Grade 12+ / University" = "#d7191c"  # Red
)

# 5. Build 100% stacked bar chart

chosen_font <- "sans"

p <- ggplot(df_summary, aes(x = Source, y = Percentage, fill = Grade_Level)) +
  geom_col(
    position = position_stack(reverse = TRUE), # Flips bar segment order
    width = 0.55, 
    color = "black", 
    linewidth = 0.4
  ) +
  geom_text(
    aes(
      label = ifelse(Percentage > 0.03, percent(Percentage, accuracy = 0.1), ""),
      group = Grade_Level
    ),
    position = position_stack(vjust = 0.5, reverse = TRUE), # Aligns percentage text
    color = "#1A1A1A",
    fontface = "bold",
    size = 2.5,
    family = chosen_font
  ) +
  coord_flip() +
  scale_y_continuous(labels = percent_format(accuracy = 1), expand = c(0, 0)) +
  scale_fill_manual(
    values = grade_colors,
    drop = FALSE,
    guide = guide_legend(reverse = FALSE) # Flips legend order to match bars
  ) +
  labs(
    title = "Perceived Reading Grade Level Comparison",
    x = "Summary Source",
    y = "Percentage of Total Evaluations",
    fill = "Reading Grade Level"
  ) +
  theme_minimal(base_size = 12, base_family = chosen_font) +
  theme(
    panel.background      = element_rect(fill = "transparent", color = NA),
    plot.background       = element_rect(fill = "transparent", color = NA),
    legend.background     = element_rect(fill = "transparent", color = NA),
    legend.box.background = element_rect(fill = "transparent", color = NA),
    text        = element_text(color = "black"),
    axis.text   = element_text(color = "black"),
    axis.title  = element_text(color = "black", size = 11),
    plot.title  = element_text(color = "black", face = "bold", size = 13),
    legend.text = element_text(color = "black"),
    legend.title= element_text(color = "black"),
    panel.grid.major.y = element_blank(),
    panel.grid.major.x = element_line(color = "black", linewidth = 0.2, linetype = "dotted"),
    legend.position    = "right"
  )

# 6. Save image output with transparent background
# ggsave(
#   filename = "Reading_grade_level_7levels.png",
#   plot = p,
#   width = 11,
#   height = 3,
#   units = "in",
#   dpi = 300,
#   bg = "transparent"
# )