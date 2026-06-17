# New Hire Company Manager

ASP.NET Web Forms project targeting .NET Framework 4.6.1 with SQL Server LocalDB storage.

## What is included

- Landing page with an `asp:DataGrid` showing company identifier and company name.
- Create New button that opens the company registration page.
- Per-row edit and delete link buttons.
- DataGrid paging.
- Company registration form with required-field validation.
- Logo upload stored as `VARBINARY(MAX)` in `tblLogos`.
- Company module checkbox values stored in `tblModules`.
- Dedicated `CompanyRepository` data helper using `SqlConnection`, `SqlCommand`, and `SqlDataReader`.
- `Company` and `CompanyModule` data objects.
- SQL setup script with tables and stored procedures.

## Setup

1. Open `NewHireCompanyManager.sln` in Visual Studio.
2. Confirm .NET Framework 4.6.1 targeting pack is installed.
3. Install SQL Server Express LocalDB and SQL Server Management Studio.
4. In SSMS, connect to `(LocalDB)\MSSQLLocalDB`.
5. Run `Sql\Database.sql`.
6. Optionally run `Sql\SampleData.sql` to add example companies.
7. Build and run the solution with IIS Express.

The default connection string is in `Web.config`:

```xml
Data Source=(LocalDB)\MSSQLLocalDB;Initial Catalog=NewHireCompanyManager;Integrated Security=True;MultipleActiveResultSets=True
```

Change it only if your SQL Server LocalDB instance uses a different name.
