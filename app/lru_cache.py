class LRUCache:
    def __init__(self, max_size):
        self.max_size = max_size
        self.cache = []

    def add(self, dictionary):
        # Check if the dictionary is already in the cache
        if dictionary in self.cache:
            # Move the existing dictionary to the end of the list
            self.cache.remove(dictionary)
            self.cache.append(dictionary)
        else:
            # If the cache is full, remove the oldest (least recently used) dictionary
            if len(self.cache) >= self.max_size:
                self.cache.pop(0)
            # Add the new dictionary to the end of the list
            self.cache.append(dictionary)

    def exists(self, dictionary):
        return dictionary in self.cache

    def __str__(self):
        return str(self.cache)