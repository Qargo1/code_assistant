// C# часть
public class AIAssistant 
{
    public async Task<string> GetCodeExplanation(string codeFragment)
{
    var context = await _vectorDb.SearchAsync(codeFragment, topK: 3);
    var prompt = $"Объясни этот код:\n{codeFragment}\nКонтекст:\n{string.Join("\n", context)}";
    
    using var httpClient = new HttpClient();
    var response = await httpClient.PostAsync("http://localhost:11434/api/generate", 
        new StringContent(JsonConvert.SerializeObject(new {
            model = "mistral",
            prompt = prompt,
            stream = false
        })));
    
    return await response.Content.ReadAsStringAsync();
}
}