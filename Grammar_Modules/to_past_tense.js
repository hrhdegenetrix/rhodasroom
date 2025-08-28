// to_past_tense.js
const nlp = require('compromise');
// For date processing
const nlpDates = require('compromise-dates');
nlp.extend(nlpDates);

let input = '';

process.stdin.on('data', function(chunk) {
    input += chunk;
});

// Helper function to deduplicate arrays while preserving order
function uniqueArray(arr) {
    return [...new Set(arr)];
}

process.stdin.on('end', function() {
    const functionType = process.argv[2];
    let result;
    let doc = nlp(input);
    
    if (functionType === 'past_tense') {
        doc.verbs().toPastTense();
        result = doc.text();
    } else if (functionType === 'people') {
        // Deduplicate people names
        result = uniqueArray(doc.people().out('array'));
    } else if (functionType === 'phone_numbers') {
        // Deduplicate phone numbers
        result = uniqueArray(doc.phoneNumbers().out('array'));
    } else if (functionType === 'locations') {
        // Deduplicate locations
        result = uniqueArray(doc.places().out('array'));
    } else if (functionType === 'dates') {
        result = doc.dates().json({ normal: true });
    } else if (functionType === 'times') {
        result = doc.times().json({ normal: true });
    } else if (functionType === 'nouns') {
        // Deduplicate nouns
        result = uniqueArray(doc.nouns().out('array'));
    } else if (functionType === 'verbs') {
        // Deduplicate verbs
        result = uniqueArray(doc.verbs().out('array'));
    } else if (functionType === 'unique_words') {
        // Simpler implementation using .out()
        const allWords = doc.terms().out('array');
        const wordCounts = {};
        
        // Count word occurrences
        allWords.forEach(word => {
            // Skip short words and common function words
            if (word.length <= 2 || /^(the|me|him|her|she|it|hers|his|we|I|i|and|or|but|a|an|of|for|in|on|at|to|by|with)$/i.test(word)) {
                return;
            }
            
            const normalized = word.toLowerCase();
            wordCounts[normalized] = (wordCounts[normalized] || 0) + 1;
        });
        
        // Get words that appear only once
        result = Object.keys(wordCounts).filter(word => wordCounts[word] === 1);
    } else if (functionType === 'extract_all') {
        // Extract people, places, dates, times in one call - deduplicate arrays
        result = {
            people: uniqueArray(doc.people().out('array')),
            places: uniqueArray(doc.places().out('array')),
            dates: doc.dates().json({ normal: true }),
            times: doc.times().json({ normal: true }),
            nouns: uniqueArray(doc.nouns().out('array')),
            verbs: uniqueArray(doc.verbs().out('array'))
        };
    } else if (functionType === 'combined_context') {
        // Extract key entities and format them as readable text
        const people = uniqueArray(doc.people().out('array'));
        const places = uniqueArray(doc.places().out('array'));
        const dates = doc.dates().json({ normal: true });
        const organizations = uniqueArray(doc.organizations().out('array'));
        
        // Format dates in a readable way
        const formattedDates = dates.map(date => {
            if (date.normal && date.text) {
                return date.text;
            }
            return date.text || '';
        });
        
        // Create a descriptive context object with formatted text
        result = {
            context: {
                people: people.length > 0 ? people.join(', ') : '',
                places: places.length > 0 ? places.join(', ') : '',
                dates: formattedDates.length > 0 ? formattedDates.join(', ') : '',
                organizations: organizations.length > 0 ? organizations.join(', ') : ''
            },
            // Also include the raw arrays for programmatic use
            raw: {
                people: people,
                places: places,
                dates: dates,
                organizations: organizations
            }
        };
    }
    
    // Output as JSON
    process.stdout.write(JSON.stringify(result));
});
