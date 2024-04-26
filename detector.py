from simhash import SimhashIndex, Simhash

class URLDuplicateDetector:
    #seting threshold to 3: lower threshold means more sensitive, less urls received
    def __init__(self, threshold = 3):
        self.simhash_index = SimhashIndex([], k=threshold)
        
    def is_duplicate(self, simhash):
        duplicates = self.simhash_index.get_near_dups(simhash)
        return len(duplicates) > 0
    
    def add_to_sh_index(self, url, simhash):
        #add url's simhash index to list
        self.simhash_index.add(url, simhash)
        
