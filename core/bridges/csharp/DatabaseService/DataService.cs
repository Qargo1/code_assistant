public class DatabaseService : IDatabaseService {
    private readonly AppDbContext _context;

    public DatabaseService(string connectionString) {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseSqlServer(connectionString)
            .Options;
        
        _context = new AppDbContext(options);
    }

    public List<Dictionary<string, object>> Query(string sql) {
        using var command = _context.Database.GetDbConnection().CreateCommand();
        command.CommandText = sql;
        _context.Database.OpenConnection();
        
        using var result = command.ExecuteReader();
        return ConvertToDictionaryList(result);
    }

    private List<Dictionary<string, object>> ConvertToDictionaryList(DbDataReader reader) {
        var results = new List<Dictionary<string, object>>();
        while (reader.Read()) {
            var row = new Dictionary<string, object>();
            for (var i = 0; i < reader.FieldCount; i++) {
                row[reader.GetName(i)] = reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }
}