library(tidyverse)
library(here)

# 1. Read CSV
df <- read.csv(here("data","Survey_Data_IntegratedSheet.csv"), check.names = FALSE)

# 2. Select Abstract and Full Text columns by exact text matching
abs_data <- df %>% select(contains("How accurately did Abstract Summary"))
ft_data  <- df %>% select(contains("How accurately did Full Text Summary"))

# 3. Combine into a clean dataset, explicitly removing NA values
df_clean <- bind_rows(
  data.frame(Source = "Abstract",  Raw = unlist(abs_data), stringsAsFactors = FALSE),
  data.frame(Source = "Full Text", Raw = unlist(ft_data), stringsAsFactors = FALSE)
) %>%
  # Filter out missing strings/NAs explicitly
  filter(!is.na(Raw) & Raw != "" & Raw != "NA") %>%
  mutate(Rating = case_when(
    grepl("Extremely inaccurately", Raw) ~ "Extremely inaccurate",
    grepl("Mostly inaccurately",    Raw) ~ "Mostly inaccurate",
    grepl("Moderately accurately",  Raw) ~ "Moderately accurate",
    grepl("Mostly accurately",      Raw) ~ "Mostly accurate",
    grepl("Extremely accurately",   Raw) ~ "Extremely accurate",
    TRUE ~ NA_character_
  )) %>%
  # Drop any leftover non-matching rows
  filter(!is.na(Rating)) %>%
  # Convert to Factor with EXACTLY 5 categories (No NA factor level)
  mutate(
    Rating = factor(Rating, levels = c(
      "Extremely accurate", 
      "Mostly accurate", 
      "Moderately accurate", 
      "Mostly inaccurate", 
      "Extremely inaccurate"
    )),
    Source = factor(Source, levels = c("Full Text", "Abstract"))
  )

# 4. Calculate proportions based ONLY on valid answers
df_summary <- df_clean %>%
  count(Source, Rating) %>%
  group_by(Source) %>%
  mutate(
    Percentage = (n / sum(n)) * 100,
    Label = ifelse(Percentage >= 5, paste0(sprintf("%.1f", Percentage), "%"), "")
  ) %>%
  ungroup()

# 5. Color map containing ONLY the 5 valid categories
colors <- c(
  "Extremely accurate"   = "#2b7bba", 
  "Mostly accurate"      = "#a6d9e8", 
  "Moderately accurate"  = "#ffffcc", 
  "Mostly inaccurate"    = "#fdbb74", 
  "Extremely inaccurate" = "#e31a1c"
)



# 6. Plot chart
ggplot(df_summary, aes(x = Source, y = Percentage, fill = Rating)) +
  # 1. Reverse the bar stacking order
  geom_col(
    position = position_stack(reverse = FALSE), # Flips bar segment order
    width = 0.55, 
    color = "black", 
    linewidth = 0.4
  )+
  coord_flip() +
  geom_text(
    aes(label = Label),
    # 2. Reverse the text position to match the bars
    position = position_stack(vjust = 0.5, reverse = FALSE),
    size = 3, fontface = "bold", color = "black"
  ) +
  scale_fill_manual(values = colors, guide = guide_legend(reverse = TRUE)) + 
  scale_y_continuous(labels = function(x) paste0(x, "%"), limits = c(0, 100), expand = c(0, 0)) +
  labs(
    title = "Summary Accuracy Rating Comparison",
    x = "Summary Source",
    y = "Percentage of Total Valid Evaluations",
    fill = "Accuracy Rating"
  ) +
  theme_minimal(base_size = 12) +
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
    legend.position    = "right",
    plot.margin     = margin(t = 15, r = 20, b = 15, l = 15, unit = "pt")
  )

# 
# ggsave("accuracy_comparison.png", 
#        width = 11,
#        height = 3,
#        units = "in",
#        dpi = 300,
#        bg = "transparent"
# )
