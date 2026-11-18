library(tidyverse)
library(here)

# 1. Read the dataset
df <- read.csv(here("data","Survey_Data_IntegratedSheet.csv"), check.names = FALSE)

# 2. Extract column BF (index 58), extract standard category labels, and calculate proportions
df_likert <- df %>%
  select(response = 58) %>%
  drop_na() %>%
  mutate(category = case_when(
    grepl("Not at all", response)    ~ "Not at all",
    grepl("Slightly", response)      ~ "Slightly",
    grepl("Moderately", response)    ~ "Moderately",
    grepl("Significantly", response) ~ "Significantly",
    grepl("Completely", response)    ~ "Completely",
    TRUE ~ response
  )) %>%
  # Preserve logical order from least to most reduced concern
  mutate(category = factor(category, levels = c("Not at all", "Slightly", "Moderately", "Significantly", "Completely"))) %>%
  count(category) %>%
  mutate(
    item = "In-Text Citations", # Single bar placeholder for horizontal layout
    percentage = n / sum(n) * 100,
    # Hide labels for very small segments (e.g., < 3%) to prevent text overlap; adjust threshold if needed
    label = ifelse(percentage >= 5, paste0(round(percentage, 1), "%"), "")
  )

# Define 5-color Blues palette matching your original scale_fill_brewer(palette = "Blues")
colors <- c(
  "Not at all"    = "#EFF3FF",
  "Slightly"      = "#BDD7E7",
  "Moderately"    = "#6BAED6",
  "Significantly" = "#3182BD",
  "Completely"    = "#08519C"
)

# 3. Plot the horizontal Likert-style stacked bar chart
ggplot(df_likert, aes(x = item, y = percentage, fill = category)) +
  geom_col(
    position = position_stack(reverse = TRUE), # Places "Not at all" on the left and "Completely" on the right
    width = 0.45,
    color = "black",
    linewidth = 0.4
  ) +
  coord_flip() +
  geom_text(
    aes(label = label),
    position = position_stack(vjust = 0.5, reverse = TRUE),
    size = 3,
    fontface = "bold",
    # Switch text color to white on the darkest blue segments for readability
    color = ifelse(df_likert$category %in% c("Significantly", "Completely"), "white", "black")
  ) +
  scale_fill_manual(values = colors) +
  scale_y_continuous(
    labels = function(x) paste0(x, "%"),
    limits = c(0, 100.1), # Slight buffer prevents floating-point rounding (100.0001%) from dropping the last bar
    expand = c(0, 0)
  ) +
  labs(
    title = "Reduction in AI Hallucinations Concern via In-Text Citations",
    x = NULL,
    y = "Percentage of Respondents",
    fill = "Response Level"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.background      = element_rect(fill = "transparent", color = NA),
    plot.background       = element_rect(fill = "transparent", color = NA),
    legend.background     = element_rect(fill = "transparent", color = NA),
    legend.box.background = element_rect(fill = "transparent", color = NA),
    text                  = element_text(color = "black"),
    axis.text.y           = element_blank(), # Hides the placeholder y-axis label for a single bar
    axis.ticks.y          = element_blank(),
    axis.text.x           = element_text(color = "black"),
    axis.title            = element_text(color = "black", size = 11),
    plot.title            = element_text(color = "black", face = "bold", size = 13),
    legend.text           = element_text(color = "black"),
    legend.title          = element_text(color = "black", face = "bold"),
    panel.grid.major.y    = element_blank(),
    panel.grid.major.x    = element_line(color = "black", linewidth = 0.2, linetype = "dotted"),
    legend.position       = "right",
    plot.margin     = margin(t = 15, r = 20, b = 15, l = 15, unit = "pt")
  )

# Adjusted dimensions to fit a wide single horizontal bar cleanly
# ggsave("hallucination_concern_likert.png", width = 14,
#        height = 5,
#        units = "in",
#        dpi = 300,
#        bg = "transparent")
