# 1. Load necessary basic packages
library(ggplot2)
library(tidyr)
library(dplyr)
library(patchwork)
library(ggsignif)
library(forcats)
library(here)
library(effectsize)

# 2. Read the data from data folder
data <- read.csv(
  here("data", "Summaries_Table.csv"), 
  check.names = FALSE
)


# 3. Define a global theme
global_theme <- theme_bw() + theme(
  panel.grid.minor = element_blank(), 
  legend.position = "none",  
  axis.title = element_text(size = 12, face = "bold"),
  axis.text = element_text(size = 10),
  axis.title.y = element_blank(),
  plot.title = element_text(size = 12, face = "bold", hjust = 0.5)
)

# NEW: Define paired Wilcoxon test with Bonferroni correction across the 6 metrics
wilcox_bonf <- function(x, y, n_tests = 6, ...) {
  res <- wilcox.test(x, y, paired = TRUE, ...)
  res$p.value <- p.adjust(res$p.value, method = "bonferroni", n = n_tests)
  res
}

# =========================================================================
# METRIC 1: Flesch-Kincaid Grade
# =========================================================================
# Extract
FKGrade <- data %>% select(pmid, Abstract_Flesch_Kincaid_Grade, FullText_Flesch_Kincaid_Grade)
# Rename columns to make the plot labels look clean
colnames(FKGrade) <- c("pmid", "Abstract", "Full Text")
# Pivot
FKGrade_long <- pivot_longer(FKGrade, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_FKGrade <- ggplot(FKGrade_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) + 
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "Flesch-Kincaid Grade") +
  global_theme


# =========================================================================
# METRIC 2: Flesch Reading Ease
# =========================================================================
# Extract
FKEase <- data %>% select(pmid, Abstract_Flesch_Reading_Ease, FullText_Flesch_Reading_Ease)
colnames(FKEase) <- c("pmid", "Abstract", "Full Text")
# Pivot
FKEase_long <- pivot_longer(FKEase, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_FKEase <- ggplot(FKEase_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) +
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "Flesch Reading Ease") +
  global_theme


# =========================================================================
# METRIC 3: SMOG Index
# =========================================================================
# Extract
SMOG <- data %>% select(pmid, Abstract_SMOG_Index, FullText_SMOG_Index)
colnames(SMOG) <- c("pmid", "Abstract", "Full Text")
# Pivot
SMOG_long <- pivot_longer(SMOG, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_SMOG <- ggplot(SMOG_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) +
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "SMOG Index") +
  global_theme


# =========================================================================
# METRIC 4: Gunning Fog Score
# =========================================================================
# Extract
GunFog <- data %>% select(pmid, Abstract_Gunning_Fog_Score, FullText_Gunning_Fog_Score)
colnames(GunFog) <- c("pmid", "Abstract", "Full Text")
# Pivot
GunFog_long <- pivot_longer(GunFog, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_GunFog <- ggplot(GunFog_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) +
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "Gunning Fog Score") +
  global_theme


# =========================================================================
# METRIC 5: RAGAS Faithfulness (GPT-5.1)
# =========================================================================
# Extract
Faith <- data %>% select(pmid, Abstract_RAGAS_Faithfulness_gpt5.1, FullText_RAGAS_Faithfulness_gpt5.1)
colnames(Faith) <- c("pmid", "Abstract", "Full Text")
# Pivot
Faith_long <- pivot_longer(Faith, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_Faith <- ggplot(Faith_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) +
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "RAGAS Faithfulness") +
  global_theme


# =========================================================================
# METRIC 6: RAGAS Summarization
# =========================================================================
# Extract
Summ <- data %>% select(pmid, Abstract_RAGAS_Summarization_Score, FullText_RAGAS_Summarization_Score)
colnames(Summ) <- c("pmid", "Abstract", "Full Text")
# Pivot
Summ_long <- pivot_longer(Summ, cols = c("Abstract", "Full Text"), names_to = "Text_Type", values_to = "Score")

# Plot
Plot_Summ <- ggplot(Summ_long, aes(x = fct_rev(Text_Type), y = Score, fill = Text_Type)) +
  geom_violin(alpha = 0.5) +
  geom_boxplot(width = 0.2, fill = "white", outlier.shape = NA) +
  geom_line(aes(group = pmid), color = "gray50", alpha = 0.25, linewidth = 0.5) + 
  geom_point(alpha = 0.5, size = 1.5) +
  geom_signif(comparisons = list(c("Abstract", "Full Text")), test = wilcox_bonf, map_signif_level = FALSE) +
  coord_flip() +  
  labs(title = "RAGAS Summarization") +
  global_theme


# =========================================================================
# COMBINE AND SAVE
# =========================================================================
# Arrange them in a 3-row by 2-column grid
Combined_Plot <- (Plot_FKEase | Plot_FKGrade) / 
  (Plot_SMOG | Plot_GunFog) / 
  (Plot_Faith | Plot_Summ)

# Display in R
print(Combined_Plot)

# Save the final figure
ggsave("Updated_Figure_6Metrics.png", Combined_Plot, width = 10, height = 12, dpi = 300)




# 1. Effect size for Flesch Reading Ease
rank_biserial(data$Abstract_Flesch_Reading_Ease, data$FullText_Flesch_Reading_Ease, paired = TRUE)

# 2. Effect size for Flesch-Kincaid Grade Score
rank_biserial(data$Abstract_Flesch_Kincaid_Grade, data$FullText_Flesch_Kincaid_Grade, paired = TRUE)

# 3. Effect size for SMOG
rank_biserial(data$Abstract_SMOG_Index, data$FullText_SMOG_Index, paired = TRUE)

# 4. Effect size for Gunning Fog
rank_biserial(data$Abstract_Gunning_Fog_Score, data$FullText_Gunning_Fog_Score, paired = TRUE)

# 5. Effect size for RAGAS Faithfulness
rank_biserial(data$Abstract_RAGAS_Faithfulness_gpt5.1, data$FullText_RAGAS_Faithfulness_gpt5.1, paired = TRUE)

# 6. Effect size for RAGAS Summarization
rank_biserial(data$Abstract_RAGAS_Summarization_Score, data$FullText_RAGAS_Summarization_Score, paired = TRUE)