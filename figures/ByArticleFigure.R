library(ggplot2)
library(tidyr)
library(dplyr)
library(patchwork)
library(here)

Human_Metrics <- read.csv(here("data","Final_LongMetrics_NoAccuracy.csv"), check.names=FALSE)
Summaries <- read.csv(here("data", "Summaries_Table.csv"), check.names=FALSE)

All_Summaries <- Human_Metrics |>
  mutate(`Article #` = if_else(`Article_ID`>50, `Article_ID`-50, `Article_ID`), Article_type=if_else(`Article_ID`>50, "Full Text", "Abstract"))

Abstracts <- All_Summaries %>% filter(Article_type == "Abstract")
FullTexts <- All_Summaries %>% filter(Article_type == "Full Text")

# Plot all individual rater points
AbstractPlot <- ggplot(Summaries, aes(x = `Article #`)) +
  geom_boxplot(data = Abstracts, aes(y = `Grade_Score`*2, group = `Article #`, color = "Human Reviewer Grade"),
               alpha = 0.3, width = 0.3) +
  # All individual human rater points
  geom_point(data = Abstracts, aes(y = `Grade_Score`*2, color = "Human Reviewer Grade"),
             size = 2, shape = 16, alpha = 0.4) +
  # FK Grade scores
  geom_point(aes(y = `Abstract_Flesch_Kincaid_Grade`, color = "Flesch-Kincaid Grade"),
             size = 3, shape = 18) +
  #SMOG Index score
  geom_point(aes(y = `Abstract_SMOG_Index`, color = "SMOG Index"),
             size = 2, shape = 17) +
  # #Gunning Fog score
  # geom_point(aes(y = `Abstract_Gunning_Fog_Score`, color = "Gunning Fog Score"),
  #            size = 2, shape = 15) +
  scale_color_discrete(breaks = c("Flesch-Kincaid Grade", "Gunning Fog Score", "SMOG Index", "Human Reviewer Grade"))+
  scale_x_continuous(breaks = seq(1, 50, by = 1)) +
  scale_y_continuous(
    breaks = seq(2, 14, by = 2),
    limits = c(1, 14),
    sec.axis = sec_axis(
      transform = ~ . / 2, # Divides 1-14 values by 2 to get 1-7 equivalents
      name = "Survey Equivalent (1-7 Likert Grade Level Scale)",
      breaks = 1:7) 
    )+
  labs(x = "Article ID",
       y = "Grade Level",
       color = "Grade Score Type",
       title = "Grade Level Scoring - Abstracts") +
  theme_bw() +  # Clean white background
  theme(
    panel.grid.minor = element_blank(),  # Remove minor gridlines
    legend.position = "right",  # Position on right of the plot
    legend.background = element_rect(fill = "white", color = "black"),
    axis.title = element_text(size = 9, face = "bold"),
    axis.text = element_text(size = 9),
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 10),
    plot.title = element_text(size = 12, face = "bold", hjust = 0.5)

  )

FullTextPlot <- ggplot(Summaries, aes(x = `Article #`)) +
  geom_boxplot(data = FullTexts, aes(y = `Grade_Score`*2, group = `Article #`, color = "Human Reviewer Grade"),
               alpha = 0.3, width = 0.3) +
  # All individual human rater points
  geom_point(data = FullTexts, aes(y = `Grade_Score`*2, color = "Human Reviewer Grade"),
             size = 2, shape = 16, alpha = 0.4) +
  # FK Grade scores
  geom_point(aes(y = `FullText_Flesch_Kincaid_Grade`, color = "Flesch-Kincaid Grade"),
             size = 3, shape = 18) +
  #SMOG Index score
  geom_point(aes(y = `FullText_SMOG_Index`, color = "SMOG Index"),
             size = 2, shape = 17) +
  # #Gunning Fog score
  # geom_point(aes(y = `FullText_Gunning_Fog_Score`, color = "Gunning Fog Score"),
  #            size = 2, shape = 15) +
  scale_color_discrete(breaks = c("Flesch-Kincaid Grade", "Gunning Fog Score", "SMOG Index", "Human Reviewer Grade"))+
  scale_x_continuous(breaks = seq(1, 50, by = 1)) +
  scale_y_continuous(
    breaks = seq(2, 14, by = 2),
    limits = c(1, 14),
    sec.axis = sec_axis(
      transform = ~ . / 2, # Divides 1-14 values by 2 to get 1-7 equivalents
      name = "Survey Equivalent (1-7 Likert Grade Level Scale)",
      breaks = 1:7) 
  )+
  labs(x = "Article ID",
       y = "Grade Level",
       color = "Grade Score Type",
       title = "Grade Level Scoring - Full Texts") +
  theme_bw() +  # Clean white background
  theme(
    panel.grid.minor = element_blank(),  # Remove minor gridlines
    legend.position = "right",  # Position on right of the plot
    legend.background = element_rect(fill = "white", color = "black"),
    axis.title = element_text(size = 9, face = "bold"),
    axis.text = element_text(size = 9),
    legend.title = element_text(size = 11, face = "bold"),
    legend.text = element_text(size = 10),
    plot.title = element_text(size = 12, face = "bold", hjust = 0.5)
    
  )

# AbstractPlot
# FullTextPlot

Combined <- AbstractPlot/FullTextPlot
# ggsave("ByArticle.png", Combined, width = 12, height = 7, dpi = 300)
Combined