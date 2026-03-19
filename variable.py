
publication_name = "Salem Mania"        
issue_number     = 1                     
article_cap      = 15
pitch_season_open = True              
articles_published = 1                  
slots_remaining  = article_cap - articles_published  

print(f"{publication_name} — Issue {issue_number}")
print(f"{slots_remaining} slots remaining this season.")

sections = ["Film", "Music", "Culture", "Literature", "Opinion", "Poetry"]

# Access items
print(sections[0])      
print(sections[-1])      

# Add a new section
sections.append("Other")
print(len(sections))   
