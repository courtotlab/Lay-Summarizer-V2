library(tidyverse)
library(scales)
library(here)

# 1. Load and process data
df_raw <- read_csv(here("data","Survey_Data_IntegratedSheet.csv"))

df_long <- df_raw %>%
  pivot_longer(
    cols = matches("clarity", ignore.case = TRUE),
    names_to = "Question_Header",
    values_to = "Raw_Response"
  ) %>%
  drop_na(Raw_Response) %>%
  mutate(
    Summary_Num = as.numeric(str_extract(Question_Header, "\\d+")),
    Source = if_else(Summary_Num <= 5, "Full Text", "Abstract"),
    Clean_Response = case_when(
      str_detect(Raw_Response, "Extremely clear")  ~ "Extremely clear",
      str_detect(Raw_Response, "Mostly clear")     ~ "Mostly clear",
      str_detect(Raw_Response, "Moderately clear") ~ "Moderately clear",
      str_detect(Raw_Response, "Somewhat unclear") ~ "Somewhat unclear",
      str_detect(Raw_Response, "Very unclear")     ~ "Very unclear",
      TRUE ~ NA_character_
    ),
    Likert_Level = factor(
      Clean_Response,
      levels = c(
        "Very unclear",
        "Somewhat unclear",
        "Moderately clear",
        "Mostly clear",
        "Extremely clear"
      ),
      ordered = TRUE
    )
  )

# 2. Aggregate percentages
df_summary <- df_long %>%
  count(Source, Likert_Level, .drop = FALSE) %>%
  group_by(Source) %>%
  mutate(Percentage = n / sum(n)) %>%
  ungroup()

# Force "Full Text" to be at the top of the horizontal chart
df_summary$Source <- factor(df_summary$Source, levels = c("Full Text", "Abstract"))

# 3. Define 5-point Likert palette
likert_colors <- c(
  "Very unclear"     = "#d7191c",
  "Somewhat unclear" = "#fdae61",
  "Moderately clear" = "#ffffbf",
  "Mostly clear"     = "#abd9e9",
  "Extremely clear"  = "#2c7bb6"
)

chosen_font <- "sans"

# 4. Generate horizontal 100% stacked bar chart
ggplot(df_summary, aes(x = Source, y = Percentage, fill = Likert_Level)) +
  geom_col(width = 0.55, color = "black", linewidth = 0.4, position = position_stack(reverse = TRUE)) +
  geom_text(
    aes(
      label = ifelse(Percentage > 0.03, percent(Percentage, accuracy = 0.1), ""),
      group = Likert_Level  # CRITICAL: Forces text to stack identically to geom_col
    ),
    position = position_stack(vjust = 0.5, reverse = TRUE),
    color = "black",
    fontface = "bold",
    size = 3
  ) +
  coord_flip() +
  scale_y_continuous(labels = percent_format(accuracy = 1), expand = c(0, 0)) +
  scale_fill_manual(
    values = likert_colors, 
    drop = FALSE,
    guide = guide_legend(reverse = FALSE) # FALSE aligns legend top-to-bottom with bar left-to-right
  ) +
  labs(
    title = "Summary Clarity Rating Comparison",
    x = "Summary Source",
    y = "Percentage of Total Evaluations",
    fill = "Clarity Rating"
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

# ggsave("clarity_chart.png",
#        width = 11,
#        height = 3,
#        units = "in",
#        dpi = 300,
#        bg = "transparent")
