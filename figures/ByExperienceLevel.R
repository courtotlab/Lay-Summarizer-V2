library(tidyverse)
library(patchwork)
library(here)

Human_Metrics <- read.csv(here("data","Final_LongMetrics_NoAccuracy.csv"), check.names=FALSE)
Accuracy <- read.csv(here("data","Final_LongMetrics_OnlyAccuracy.csv"), check.names=FALSE)

df_long <- Human_Metrics %>%
  rename(
    participant = `Participant_IDs`,
    experience_level = `Experience_Level`,
    grade_score = `Grade_Score`
  ) %>%
  pivot_longer(
    cols = c(Clarity, Appropriateness, `Jargon_Avoided`, grade_score),
    names_to = "item",
    values_to = "rating"
  ) %>%
  mutate(
    experience_level = factor(experience_level, levels = 1:5, ordered = TRUE),
    item = if_else(item == "grade_score", "Grade_Score", item)
  )

df_accuracy <- Accuracy %>%
  select(-c(`Accuracy_ID`,`Accurate_Abstract`,`Accurate_Full-Text`)) %>%
  rename(
    participant = `Participant_IDs`,
    FullText_acc = `Full_Text_Score`,
    Abstract_acc = `Abstract_Score`,
    experience_level = `Experience_Level`
  ) %>%
  pivot_longer(
    cols = c(Abstract_acc, FullText_acc),
    names_to = "item",
    values_to = "rating"
  ) %>%
  mutate(
    experience_level = factor(experience_level, levels = 1:5, ordered = TRUE)
  ) %>%
  filter(!is.na(rating) & rating !="")

df_filtered <- df_long %>%
  select(-c(`Article_ID`, `Group`))

df_clean <- rbind(df_filtered, df_accuracy) %>%
  mutate(item = case_when(
    item %in% c("Abstract_acc", "FullText_acc") ~ "Accuracy",
    TRUE ~ item
  ))


no_grade_score <- df_clean %>%
  filter(item != "Grade_Score") %>%
  mutate(experience_level = factor(experience_level, levels = 1:5))


# --- 1. Data Prep for Diverging Likert Plot ---
prop_df <- no_grade_score %>%
  count(item, experience_level, rating) %>%
  group_by(item, experience_level) %>%
  mutate(pct = n / sum(n) * 100) %>%
  ungroup()

# Negative side: rating 3 (half) -> 2 -> 1
neg_df <- prop_df %>%
  filter(rating %in% c(1, 2, 3)) %>%
  mutate(
    value = if_else(rating == 3, -pct / 2, -pct),
    rating = factor(rating, levels = c(3, 2, 1))
  ) %>%
  arrange(item, experience_level, rating) %>%
  group_by(item, experience_level) %>%
  mutate(
    cum = cumsum(value),
    xmax = lag(cum, default = 0),
    xmin = cum
  ) %>%
  ungroup()

# Positive side: rating 3 (half) -> 4 -> 5
pos_df <- prop_df %>%
  filter(rating %in% c(3, 4, 5)) %>%
  mutate(
    value = if_else(rating == 3, pct / 2, pct),
    rating = factor(rating, levels = c(3, 4, 5))
  ) %>%
  arrange(item, experience_level, rating) %>%
  group_by(item, experience_level) %>%
  mutate(
    cum = cumsum(value),
    xmin = lag(cum, default = 0),
    xmax = cum
  ) %>%
  ungroup()

# plot_df <- bind_rows(neg_df, pos_df) %>%
#   mutate(
#     rating = factor(rating, levels = c("1", "2", "3", "4", "5")),
#     y_num  = as.numeric(experience_level)
#   )

plot_df <- bind_rows(neg_df, pos_df) %>%
  mutate(
    rating = factor(rating, levels = c("1", "2", "3", "4", "5")),
    y_num  = as.numeric(experience_level),
    x_mid  = (xmin + xmax) / 2,
    # Avoid duplicate labels for rating 3: show only on pos_df (where xmin >= 0)
    label_txt = case_when(
      rating == "3" & xmin < 0 ~ "",
      pct >= 5                 ~ as.character(n),
      TRUE                     ~ ""
    )
  )

item_labels <- c(
  "Appropriateness" = "Appropriateness for Lay Audience",
  "Clarity" = "Clarity",
  "Jargon_Avoided" = "Jargon Avoided",
  "Accuracy" = "Accuracy to Source Article",
  "Grade_Score" = "Grade Level Perceived"
)


# --- 2. Diverging Likert Plot ---
ExperiencePlot <- ggplot(plot_df) +
  geom_rect(
    aes(
      xmin = xmin, xmax = xmax,
      ymin = y_num - 0.35, ymax = y_num + 0.35,
      fill = rating
    ),
    color = "white", linewidth = 0.3
  ) +
  
  geom_text(
    aes(x = x_mid, y = y_num, label = label_txt),
    size = 2.8, fontface = "bold", color = "grey15"
  ) +
  
  geom_vline(xintercept = 0, color = "grey30", linetype = "dashed", linewidth = 0.6) +
  facet_wrap(~ item, ncol =1, labeller = as_labeller(item_labels)) +
  scale_fill_brewer(palette = "RdYlBu", direction = 1) +
  scale_y_continuous(breaks = 1:5, labels = 1:5) +
  scale_x_continuous(labels = function(x) paste0(abs(x), "%")) +
  labs(x = NULL, y = "Experience Level", fill = "5-Point Rating") +
  theme_bw() +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    legend.position = "right",
    legend.background = element_rect(fill = "white", color = "black"),
    axis.title = element_text(size = 12, face = "bold"),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 10),
    plot.title = element_text(size = 12, face = "bold", hjust = 0.5),
    strip.background = element_rect(fill = "grey90", color = "black"),
    strip.text = element_text(size = 10, face = "bold"),
    legend.box.margin = margin(t = 0, r = 5, b = 0, l = 15, unit = "pt")
  )


# --- 1. Data Prep for 1-7 Scale (Grade_Score) ---
grade_df <- df_clean %>%
  filter(item == "Grade_Score") %>%
  mutate(
    experience_level = factor(experience_level, levels = 1:5),
    rating = factor(rating, levels = 1:7)
  )

prop_grade <- grade_df %>%
  count(item, experience_level, rating) %>%
  group_by(experience_level) %>%
  mutate(pct = n / sum(n) * 100) %>%
  ungroup()

# Negative side: rating 4 (half) -> 3 -> 2 -> 1
neg_grade <- prop_grade %>%
  filter(rating %in% c(1, 2, 3, 4)) %>%
  mutate(
    value = if_else(rating == 4, -pct / 2, -pct),
    rating = factor(rating, levels = c(4, 3, 2, 1))
  ) %>%
  arrange(experience_level, rating) %>%
  group_by(experience_level) %>%
  mutate(
    cum = cumsum(value),
    xmax = lag(cum, default = 0),
    xmin = cum
  ) %>%
  ungroup()

# Positive side: rating 4 (half) -> 5 -> 6 -> 7
pos_grade <- prop_grade %>%
  filter(rating %in% c(4, 5, 6, 7)) %>%
  mutate(
    value = if_else(rating == 4, pct / 2, pct),
    rating = factor(rating, levels = c(4, 5, 6, 7))
  ) %>%
  arrange(experience_level, rating) %>%
  group_by(experience_level) %>%
  mutate(
    cum = cumsum(value),
    xmin = lag(cum, default = 0),
    xmax = cum
  ) %>%
  ungroup()

# plot_grade_df <- bind_rows(neg_grade, pos_grade) %>%
#   mutate(
#     rating = factor(rating, levels = c("1", "2", "3", "4", "5", "6", "7")),
#     y_num  = as.numeric(experience_level)
#   )

plot_grade_df <- bind_rows(neg_grade, pos_grade) %>%
  mutate(
    rating = factor(rating, levels = c("1", "2", "3", "4", "5", "6", "7")),
    y_num  = as.numeric(experience_level),
    x_mid  = (xmin + xmax) / 2,
    # Avoid duplicate labels for rating 4: show only on pos_grade (where xmin >= 0)
    label_txt = case_when(
      rating == "4" & xmin < 0 ~ "",
      pct >= 5                 ~ as.character(n),
      TRUE                     ~ ""
    )
  )


#Grade level labels and colours
grade_colors <- c(
  "Grades 1 to 2"          = "#006837", # Dark Green
  "Grades 3 to 4"          = "#1a9641", # Green
  "Grades 5 to 6"          = "#a6d96a", # Light Green
  "Grades 7 to 8"          = "#ffffbf", # Soft Yellow
  "Grades 9 to 10"         = "#fdae61", # Orange
  "Grades 11 to 12"        = "#f46d43", # Dark Orange
  "Grade 12+/University" = "#d7191c"  # Red
)

# --- 2. Grade Score Plot (1-7 Scale) ---
GradeScorePlot <- ggplot(plot_grade_df) +
  geom_rect(
    aes(
      xmin = xmin, xmax = xmax,
      ymin = y_num - 0.35, ymax = y_num + 0.35,
      fill = rating
    ),
    color = "white", linewidth = 0.3
  ) +
  
  geom_text(
    aes(x = x_mid, y = y_num, label = label_txt),
    size = 2.8, fontface = "bold", color = "grey15"
  ) +
  
  
  geom_vline(xintercept = 0, color = "grey30", linetype = "dashed", linewidth = 0.6) +
  facet_wrap(~ item, ncol = 1, labeller = as_labeller(item_labels)) +
  scale_fill_manual(
    values = setNames(unname(grade_colors), as.character(1:7)),
    labels = names(grade_colors),
    drop = FALSE
  ) +
  scale_y_continuous(breaks = 1:5, labels = 1:5) +
  scale_x_continuous(labels = function(x) paste0(abs(x), "%")) +
  labs(x = "Percentage of Responses", y = "Experience Level", fill = "7-Point \nGrade Rating") +
  theme_bw() +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    legend.position = "right",
    legend.background = element_rect(fill = "white", color = "black"),
    axis.title = element_text(size = 12, face = "bold"),
    axis.text = element_text(size = 10),
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 9),
    strip.background = element_rect(fill = "grey90", color = "black"),
    strip.text = element_text(size = 10, face = "bold"),
    legend.box.margin = margin(t = 0, r = 5, b = 0, l = 15, unit = "pt")
  )

# counts <- data.frame(expertise = 1:5, n = c(0, 1, 12, 8, 4))
# p_experience <- ggplot(counts, aes(x = expertise, y = 1, label = n)) +
#   geom_point(aes(size = n, alpha = 0.4, fill = factor(expertise)), shape = 21) +
#   geom_text(size = 3, fontface = "bold") +
#   labs(x = "Number of Human Reviewers Self-Assessed at the Corresponding Experience Level") +
#   scale_fill_brewer(palette = "YlOrRd", guide = "none") +
#   scale_size_continuous(range = c(5, 20), guide = "none") +
#   scale_x_continuous(limits = c(0.65, 5.35)) +
#   theme_void() +
# 
#   theme(legend.position = "none",
#         axis.title.x = element_text(size = 12, face = "italic"))

counts <- data.frame(
  expertise = 1:5,
  n = c(0, 2, 13, 8, 7),
  label_level = paste0("Level ", 1:5)
)

p_experience <- ggplot(counts, aes(x = expertise, y = 1)) +
  # Bubble circle
  geom_point(aes(size = n, fill = factor(expertise)), shape = 21, alpha = 0.5) +
  # Reviewer count inside bubble (only when n > 0)
  geom_text(aes(label = n), size = 3.5, fontface = "bold", color = "black") +
  geom_text(aes(y = 0.5, label = label_level), size = 3, fontface = "bold", color = "grey20") +
  scale_fill_brewer(palette = "Purples", guide = "none") +
  scale_size_continuous(range = c(4, 16), guide = "none") +
  scale_x_continuous(breaks = 1:5, limits = c(0.5, 5.5)) +
  scale_y_continuous(limits = c(0.2, 1.4)) +
  labs(caption = "Number of Human Reviewers Self-Assessed at the Corresponding Experience Level") +
  theme_void() +
  theme(
    plot.caption = element_text(size = 10, face = "italic", hjust = 0.5, margin = margin(t = 2))
  )

# Define shared scale limits and 50% / 100% breaks
common_x_scale <- list(
  scale_x_continuous(
    limits = c(-100, 100),
    breaks = seq(-100, 100, by = 50),
    labels = function(x) paste0(abs(x), "%"),
    expand = c(0, 0) # removes extra padding at edges
  )
)

# Apply to ExperiencePlot
ExperiencePlot <- ExperiencePlot + common_x_scale

# Apply to GradeScorePlot
GradeScorePlot <- GradeScorePlot + common_x_scale

# --- 3. Combine with Patchwork ---
Combined <- ExperiencePlot / GradeScorePlot / p_experience + 
  plot_layout(heights = c(8, 2, 1))

Combined

# ggsave("ByExperience.png", Combined, width = 9, height = 12, dpi = 300)


